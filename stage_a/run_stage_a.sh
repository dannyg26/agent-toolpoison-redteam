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

TAU2_REPO=https://github.com/sierra-research/tau2-bench; TAU2_COMMIT=989d3285ae669e49503324bdb9981bf14fccedeb  # tag v2.0.0
log "=== setup"
pip install -q "vllm==0.33.0" uv > "$OUT/pip_vllm.log" 2>&1 || { log "FAILED pip vllm"; exit 1; }
python -m venv /root/venv_bfcl && /root/venv_bfcl/bin/pip install -q "bfcl-eval==2026.3.23" soundfile > "$OUT/pip_bfcl.log" 2>&1 \
  || { log "FAILED pip bfcl"; exit 1; }
# tau-bench is NOT the PyPI package named "tau2" (an unrelated physics tool). Install the benchmark from its
# repository at the v2.0.0 tag. It needs Python >= 3.12, so uv provides a 3.12 environment.
( git clone -q "$TAU2_REPO" /root/tau2-bench && git -C /root/tau2-bench checkout -q "$TAU2_COMMIT" &&
  uv venv -q -p 3.12 /root/venv_tau2 && uv pip install -q --python /root/venv_tau2/bin/python -e /root/tau2-bench ) \
  > "$OUT/pip_tau2.log" 2>&1 || { log "FAILED install tau2-bench"; exit 1; }
/root/venv_bfcl/bin/python "$REPO/stage_a/bfcl_adapter.py" --diff-out "$OUT/bfcl_adapter.diff" || { log "FAILED adapter"; exit 1; }
# pre-flight: every tool must import and accept our flags BEFORE any model is downloaded
/root/venv_bfcl/bin/python -c "from bfcl_eval.constants.model_config import MODEL_CONFIG_MAPPING as M; \
assert 'Qwen/Qwen3.8-27B-FC' in M and 'huihui-ai/Huihui-Qwen3.8-27B-abliterated-FC' in M" > "$OUT/preflight.log" 2>&1 \
  || { log "FAILED preflight bfcl"; tail -20 "$OUT/preflight.log"; exit 1; }
/root/venv_bfcl/bin/bfcl generate --help 2>&1 | grep -q -- "--run-ids" || { log "FAILED preflight bfcl --run-ids"; exit 1; }
( cd /root/tau2-bench && /root/venv_tau2/bin/tau2 run --help ) > "$OUT/preflight_tau2.log" 2>&1
grep -q -- "--task-ids" "$OUT/preflight_tau2.log" && grep -q -- "--user-llm" "$OUT/preflight_tau2.log" \
  || { log "FAILED preflight tau2"; tail -20 "$OUT/preflight_tau2.log"; exit 1; }
for dom in airline retail telecom; do [ -f "/root/tau2-bench/data/tau2/domains/$dom/split_tasks.json" ] \
  || { log "FAILED preflight tau2 data $dom"; exit 1; }; done
VLLM_DIR=$(python -c "import vllm,os;print(os.path.dirname(vllm.__file__))")
grep -rqsE --include='*.py' "[\"']qwen3_coder[\"']" "$VLLM_DIR" || { log "FAILED preflight vllm qwen3_coder parser"; exit 1; }
log "preflight OK"
for m in "${CHECKPOINTS[@]}" "$USER_SIM"; do                      # pin revisions before serving
  python -c "from huggingface_hub import HfApi;print('$m', HfApi().model_info('$m').sha)" >> "$OUT/revisions.txt" \
    || { log "FAILED revision $m"; exit 1; }
done

serve(){ # model port util name  -> waits until the model is listed (authenticated)
  local rev; rev=$(awk -v m="$1" '$1==m{print $2}' "$OUT/revisions.txt")
  # No --api-key (fix A3): servers listen on 127.0.0.1 only, and BFCL polls /v1/models without a key.
  nohup vllm serve "$1" --revision "$rev" --served-model-name "$4" --port "$2" --host 127.0.0.1 \
    --quantization fp8 --max-model-len 32768 --gpu-memory-utilization "$3" --max-num-seqs 32 \
    --limit-mm-per-prompt '{"image":0,"video":0}' \
    --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3 > "$OUT/serve_$2.log" 2>&1 </dev/null &
  for i in $(seq 1 240); do
    curl -s -m 3 "http://127.0.0.1:$2/v1/models" -H "Authorization: Bearer $KEY" | grep -q "\"$4\"" && {
      curl -s "http://127.0.0.1:$2/v1/models" -H "Authorization: Bearer $KEY" > "$OUT/models_$2_$(echo "$4" | tr '/' '_').json"
      log "UP $4 on $2"; return 0; }
    sleep 5
  done; log "FAILED serve $4"; tail -40 "$OUT/serve_$2.log"; return 1
}
toolcheck(){ # port name -> one chat request with a tool; the server must return a PARSED tool call (fix A4)
  python - "$1" "$2" > "$OUT/toolcheck_$1.json" 2>&1 <<'PY' || { log "FAILED toolcheck $2"; cat "$OUT/toolcheck_$1.json"; return 1; }
import json, sys, urllib.request
port, name = sys.argv[1], sys.argv[2]
body = {"model": name, "max_tokens": 4096, "temperature": 0,
        "messages": [{"role": "user", "content": "What is the weather in Paris? Use the tool."}],
        "tools": [{"type": "function", "function": {"name": "get_weather", "description": "Current weather for a city",
                   "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}]}
req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"})
msg = json.load(urllib.request.urlopen(req, timeout=600))["choices"][0]["message"]
calls = msg.get("tool_calls") or []
print(json.dumps({"tool_calls": calls, "content": (msg.get("content") or "")[:300]}))
assert calls and calls[0]["function"]["name"] == "get_weather", "no parsed tool call"
assert "city" in json.loads(calls[0]["function"]["arguments"])
PY
  log "toolcheck OK $2"
}
stop(){ pkill -f "vllm serve .*--port $1 " ; sleep 20; }

serve "$USER_SIM" 8600 0.45 user-sim || exit 1                    # the simulated user stays up throughout
toolcheck 8600 user-sim || exit 1                                  # telecom's simulated user also calls tools

for M in "${CHECKPOINTS[@]}"; do
  TAG=$(echo "$M" | tr '/' '_'); D="$OUT/$TAG"; mkdir -p "$D"
  log "=== checkpoint $M"
  serve "$M" 8500 0.47 "$M" || exit 1
  toolcheck 8500 "$M" || exit 1
  # BFCL: generate the frozen subset against the running server, then score only those IDs
  ( cd "$D" && cp "$REPO/stage_a/bfcl_test_case_ids.json" test_case_ids_to_generate.json &&
    BFCL_PROJECT_ROOT="$D" LOCAL_SERVER_ENDPOINT=127.0.0.1 LOCAL_SERVER_PORT=8500 OPENAI_API_KEY="$KEY" \
      /root/venv_bfcl/bin/bfcl generate --model "$M-FC" --run-ids --skip-server-setup --num-threads 8 \
      > "$D/bfcl_generate.log" 2>&1 &&
    BFCL_PROJECT_ROOT="$D" /root/venv_bfcl/bin/bfcl evaluate --model "$M-FC" \
      --test-category "$(python -c "import json;print(','.join(json.load(open('$REPO/stage_a/bfcl_test_case_ids.json'))))")" \
      --partial-eval > "$D/bfcl_evaluate.log" 2>&1 )
  rc=$?; log "bfcl $M exit $rc"
  [ $rc = 0 ] || { log "FAILED bfcl $M"; tail -30 "$D/bfcl_generate.log" "$D/bfcl_evaluate.log" 2>/dev/null; exit 1; }
  # tau-bench 2.0: the frozen 30 tasks, one trial each, same simulated user for both checkpoints
  for dom in airline retail telecom; do
    IDS=$(python -c "import json;print(' '.join(json.load(open('$REPO/stage_a/tau2_task_ids.json'))['$dom']))")
    ( cd /root/tau2-bench && HOSTED_VLLM_API_KEY="$KEY" /root/venv_tau2/bin/tau2 run --domain "$dom" \
      --task-split-name train --task-ids $IDS \
      --agent-llm "hosted_vllm/$M" --agent-llm-args "{\"api_base\":\"http://127.0.0.1:8500/v1\",\"api_key\":\"$KEY\"}" \
      --user-llm "hosted_vllm/user-sim" --user-llm-args "{\"api_base\":\"http://127.0.0.1:8600/v1\",\"api_key\":\"$KEY\",\"temperature\":0.0}" \
      --num-trials 1 --seed 2027 --max-concurrency 4 --save-to "$D/tau2_$dom" ) > "$D/tau2_$dom.log" 2>&1
    rc=$?; log "tau2 $M $dom exit $rc"
    [ $rc = 0 ] || { log "FAILED tau2 $M $dom"; tail -30 "$D/tau2_$dom.log"; exit 1; }
  done
  stop 8500
done
stop 8600
pip freeze 2>/dev/null | grep -iE "^(vllm|torch|transformers)==" > "$OUT/pip_versions.txt"
/root/venv_bfcl/bin/pip freeze | grep -i bfcl >> "$OUT/pip_versions.txt"; uv pip freeze --python /root/venv_tau2/bin/python | grep -iE "^-e|^tau2|litellm" >> "$OUT/pip_versions.txt"; echo "tau2-bench $TAU2_COMMIT" >> "$OUT/pip_versions.txt"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader > "$OUT/gpu.txt"
git -C "$REPO" rev-parse HEAD > "$OUT/commit.txt"; git -C "$REPO" status --porcelain | wc -l >> "$OUT/commit.txt"
log ALL_DONE
