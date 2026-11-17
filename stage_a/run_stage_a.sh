#!/bin/bash
# Stage A capability pilot (stage_a/GATE.md). Runs on one A100 80GB pod from a clone of the pushed commit.
# Outputs go to /root/out/stage_a (outside the repo). The script writes ALL_DONE at the end and never waits
# on a background server. A local watcher copies outputs back and terminates the pod.
set -u
REPO=/root/repo; OUT=/root/out/stage_a; mkdir -p "$OUT"
export VLLM_USE_FLASHINFER_SAMPLER=0
KEY=$(python -c "import secrets;print(secrets.token_hex(12))")   # local server key, never leaves the pod
USER_SIM=Qwen/Qwen3.8-27B-FP8
CHECKPOINTS=("huihui-ai/Huihui-Qwen3.8-27B-abliterated" "Qwen/Qwen3.8-27B")
log(){ echo "$* ($(date +%T))"; }

log "=== setup"
pip install -q "vllm==0.33.0" > "$OUT/pip_vllm.log" 2>&1 || { log "FAILED pip vllm"; exit 1; }
python -m venv /root/venv_bfcl && /root/venv_bfcl/bin/pip install -q "bfcl-eval==2026.3.23" > "$OUT/pip_bfcl.log" 2>&1 \
  || { log "FAILED pip bfcl"; exit 1; }
python -m venv /root/venv_tau2 && /root/venv_tau2/bin/pip install -q "tau2==4.0.1" > "$OUT/pip_tau2.log" 2>&1 \
  || { log "FAILED pip tau2"; exit 1; }
/root/venv_bfcl/bin/python "$REPO/stage_a/bfcl_adapter.py" --diff-out "$OUT/bfcl_adapter.diff" || { log "FAILED adapter"; exit 1; }
for m in "${CHECKPOINTS[@]}" "$USER_SIM"; do                      # pin revisions before serving
  python -c "from huggingface_hub import HfApi;print('$m', HfApi().model_info('$m').sha)" >> "$OUT/revisions.txt" \
    || { log "FAILED revision $m"; exit 1; }
done

serve(){ # model port util name  -> waits until the model is listed (authenticated)
  local rev; rev=$(awk -v m="$1" '$1==m{print $2}' "$OUT/revisions.txt")
  nohup vllm serve "$1" --revision "$rev" --served-model-name "$4" --port "$2" --host 127.0.0.1 --api-key "$KEY" \
    --quantization fp8 --max-model-len 32768 --gpu-memory-utilization "$3" \
    --enable-auto-tool-choice --tool-call-parser hermes --reasoning-parser qwen3 > "$OUT/serve_$2.log" 2>&1 </dev/null &
  for i in $(seq 1 240); do
    curl -s -m 3 "http://127.0.0.1:$2/v1/models" -H "Authorization: Bearer $KEY" | grep -q "\"$4\"" && {
      curl -s "http://127.0.0.1:$2/v1/models" -H "Authorization: Bearer $KEY" > "$OUT/models_$2_$(echo "$4" | tr '/' '_').json"
      log "UP $4 on $2"; return 0; }
    sleep 5
  done; log "FAILED serve $4"; tail -40 "$OUT/serve_$2.log"; return 1
}
stop(){ pkill -f "vllm serve .*--port $1 " ; sleep 20; }

serve "$USER_SIM" 8600 0.42 user-sim || exit 1                    # the simulated user stays up throughout

for M in "${CHECKPOINTS[@]}"; do
  TAG=$(echo "$M" | tr '/' '_'); D="$OUT/$TAG"; mkdir -p "$D"
  log "=== checkpoint $M"
  serve "$M" 8500 0.45 "$M" || exit 1
  # BFCL: generate the frozen subset against the running server, then score only those IDs
  ( cd "$D" && cp "$REPO/stage_a/bfcl_test_case_ids.json" test_case_ids_to_generate.json &&
    BFCL_PROJECT_ROOT="$D" LOCAL_SERVER_ENDPOINT=127.0.0.1 LOCAL_SERVER_PORT=8500 OPENAI_API_KEY="$KEY" \
      /root/venv_bfcl/bin/bfcl generate --model "$M-FC" --run-ids --skip-server-setup --num-threads 8 \
      > "$D/bfcl_generate.log" 2>&1 &&
    BFCL_PROJECT_ROOT="$D" /root/venv_bfcl/bin/bfcl evaluate --model "$M-FC" \
      --test-category "$(python -c "import json;print(','.join(json.load(open('$REPO/stage_a/bfcl_test_case_ids.json'))))")" \
      --partial-eval > "$D/bfcl_evaluate.log" 2>&1 )
  log "bfcl $M exit $?"
  # tau-bench 2.0: the frozen 30 tasks, one trial each, same simulated user for both checkpoints
  for dom in airline retail telecom; do
    IDS=$(python -c "import json;print(' '.join(json.load(open('$REPO/stage_a/tau2_task_ids.json'))['$dom']))")
    HOSTED_VLLM_API_KEY="$KEY" /root/venv_tau2/bin/tau2 run --domain "$dom" --task-split-name train --task-ids $IDS \
      --agent-llm "hosted_vllm/$M" --agent-llm-args "{\"api_base\":\"http://127.0.0.1:8500/v1\"}" \
      --user-llm "hosted_vllm/user-sim" --user-llm-args "{\"api_base\":\"http://127.0.0.1:8600/v1\",\"temperature\":0.0}" \
      --num-trials 1 --seed 2027 --max-concurrency 4 --save-to "$D/tau2_$dom" > "$D/tau2_$dom.log" 2>&1
    log "tau2 $M $dom exit $?"
  done
  stop 8500
done
stop 8600
pip freeze 2>/dev/null | grep -iE "^(vllm|torch|transformers)==" > "$OUT/pip_versions.txt"
/root/venv_bfcl/bin/pip freeze | grep -i bfcl >> "$OUT/pip_versions.txt"; /root/venv_tau2/bin/pip freeze | grep -iE "^tau2|litellm" >> "$OUT/pip_versions.txt"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader > "$OUT/gpu.txt"
git -C "$REPO" rev-parse HEAD > "$OUT/commit.txt"; git -C "$REPO" status --porcelain | wc -l >> "$OUT/commit.txt"
log ALL_DONE
