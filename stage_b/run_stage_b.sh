#!/bin/bash
# Stage B runner (stage_b/DESIGN.md) on one A100 80GB pod, from a clone of the pushed commit.
#   SPLIT=dev|test (default dev)   LIMIT=<cases, 0 = all>   TARGETS="qwen gemma"   WORKERS=16
# Two vLLM servers at a time: the TARGET on 8500 and an ATTACKER on 8600 (both FP8, text only).
# The aligned Qwen3.8-27B is both a target and the aligned attacker; when it is the target it also serves the
# aligned-attacker condition from the same server (separate conversations, nothing shared).
# Outputs go to /root/out/stage_b. Writes ALL_DONE at the end; any failure writes a FAILED line and exits.
set -u
# The former default can cost hundreds of dollars. The budget pilot is a separate explicit runner.
if [ "${ALLOW_LARGE_STUDY:-}" != "yes" ]; then
  echo 'FAILED: large-study runner disabled. Use stage_b/run_pilot.sh for the bounded pilot.'
  exit 64
fi
REPO=/root/repo; OUT=/root/out/stage_b; mkdir -p "$OUT"
SPLIT=${SPLIT:-dev}; LIMIT=${LIMIT:-0}; WORKERS=${WORKERS:-16}; TARGETS=${TARGETS:-"qwen gemma"}
export VLLM_USE_FLASHINFER_SAMPLER=0
ABL=huihui-ai/Huihui-Qwen3.8-27B-abliterated; QWEN=Qwen/Qwen3.8-27B; GEMMA=google/gemma-4-26B-A4B-it
log(){ echo "$* ($(date +%T))"; }

log "=== setup (split $SPLIT, limit $LIMIT, targets $TARGETS)"
pip install -q "vllm==0.33.0" > "$OUT/pip_vllm.log" 2>&1 || { log "FAILED pip vllm"; exit 1; }
python -m venv /root/venv_ad && /root/venv_ad/bin/pip install -q "agentdojo==0.1.35" "openai==3.52.0" \
  > "$OUT/pip_agentdojo.log" 2>&1 || { log "FAILED pip agentdojo"; exit 1; }
# pre-flight, before any model download: frozen cases reproduce, offline harness tests pass, parsers exist
/root/venv_ad/bin/python "$REPO/stage_b/select_cases.py" --check > "$OUT/preflight_cases.log" 2>&1 \
  || { log "FAILED preflight cases.json"; cat "$OUT/preflight_cases.log"; exit 1; }
/root/venv_ad/bin/python "$REPO/stage_b/test_harness.py" > "$OUT/preflight_tests.log" 2>&1 \
  || { log "FAILED preflight harness tests"; tail -30 "$OUT/preflight_tests.log"; exit 1; }
VLLM_DIR=$(python -c "import vllm,os;print(os.path.dirname(vllm.__file__))")
for p in qwen3_coder gemma4; do grep -rqsE --include='*.py' "[\"']$p[\"']" "$VLLM_DIR" \
  || { log "FAILED preflight vllm parser $p"; exit 1; }; done
log "preflight OK"
for m in $ABL $QWEN $GEMMA; do
  python -c "from huggingface_hub import HfApi;print('$m', HfApi().model_info('$m').sha)" >> "$OUT/revisions.txt" \
    || { log "FAILED revision $m"; exit 1; }
done

parsers(){ case "$1" in $GEMMA) echo "--tool-call-parser gemma4 --reasoning-parser gemma4";;
                        *) echo "--tool-call-parser qwen3_coder --reasoning-parser qwen3";; esac; }
mmlimit(){ case "$1" in $GEMMA) echo '{"image":0}';; *) echo '{"image":0,"video":0}';; esac; }  # text only
serve(){ # model port util
  local rev; rev=$(awk -v m="$1" '$1==m{print $2}' "$OUT/revisions.txt")
  nohup vllm serve "$1" --revision "$rev" --served-model-name "$1" --port "$2" --host 127.0.0.1 \
    --quantization fp8 --max-model-len 32768 --gpu-memory-utilization "$3" --max-num-seqs 32 \
    --limit-mm-per-prompt "$(mmlimit "$1")" --enable-auto-tool-choice $(parsers "$1") \
    > "$OUT/serve_$2_$(echo "$1" | tr '/' '_').log" 2>&1 </dev/null &
  for i in $(seq 1 240); do
    curl -s -m 3 "http://127.0.0.1:$2/v1/models" | grep -q "\"$1\"" && {
      curl -s "http://127.0.0.1:$2/v1/models" > "$OUT/models_$2_$(echo "$1" | tr '/' '_').json"
      log "UP $1 on $2"; toolcheck "$2" "$1"; return $?; }
    sleep 5
  done; log "FAILED serve $1"; tail -40 "$OUT/serve_$2_$(echo "$1" | tr '/' '_').log"; return 1
}
toolcheck(){ # port name -> the server must return a PARSED tool call
  python - "$1" "$2" > "$OUT/toolcheck_$1_$(echo "$2" | tr '/' '_').json" 2>&1 <<'PY' \
    || { log "FAILED toolcheck $2"; cat "$OUT/toolcheck_$1_$(echo "$2" | tr '/' '_').json"; return 1; }
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
H(){ # condition target-model target-name target-label [attacker-model attacker-url attacker-label]
  local extra=(); [ $# -ge 7 ] && extra=(--attacker-model "$5" --attacker-url "$6" --attacker-label "$7")
  ( cd "$REPO" && /root/venv_ad/bin/python stage_b/harness.py --split "$SPLIT" --limit "$LIMIT" --workers "$WORKERS" \
      --condition "$1" --target-model "$2" --target-url http://127.0.0.1:8500/v1 --target-name "$3" \
      --target-label "$4" "${extra[@]}" --out "$OUT/runs" ) >> "$OUT/harness.log" 2>&1
  local rc=$?; log "harness $1 ${7:-none} -> $4 exit $rc"
  [ $rc = 0 ] || { log "FAILED harness $1 ${7:-none} $4"; tail -30 "$OUT/harness.log"; exit 1; }
}
A=http://127.0.0.1:8600/v1; T=http://127.0.0.1:8500/v1

for tgt in $TARGETS; do
  case $tgt in qwen) TM=$QWEN; TN=Qwen;; gemma) TM=$GEMMA; TN=Gemma;; *) log "FAILED unknown target $tgt"; exit 1;; esac
  log "=== target $TM"
  serve "$TM" 8500 0.47 || exit 1
  serve "$ABL" 8600 0.45 || exit 1
  H no_attack   "$TM" "$TN" "$tgt"
  H fixed       "$TM" "$TN" "$tgt"
  H nonadaptive "$TM" "$TN" "$tgt" "$ABL" "$A" abliterated
  H adaptive    "$TM" "$TN" "$tgt" "$ABL" "$A" abliterated
  if [ "$tgt" = qwen ]; then
    H adaptive  "$TM" "$TN" "$tgt" "$QWEN" "$T" aligned          # aligned attacker = the target's own server
  else
    stop 8600; serve "$QWEN" 8600 0.45 || exit 1
    H adaptive  "$TM" "$TN" "$tgt" "$QWEN" "$A" aligned
  fi
  stop 8600; stop 8500
done
pip freeze 2>/dev/null | grep -iE "^(vllm|torch|transformers)==" > "$OUT/pip_versions.txt"
/root/venv_ad/bin/pip freeze | grep -iE "^(agentdojo|openai|pydantic)==" >> "$OUT/pip_versions.txt"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader > "$OUT/gpu.txt"
git -C "$REPO" rev-parse HEAD > "$OUT/commit.txt"; git -C "$REPO" status --porcelain | wc -l >> "$OUT/commit.txt"
log ALL_DONE
