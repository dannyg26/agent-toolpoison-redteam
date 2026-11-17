#!/bin/bash
# Explicit bounded pilot. Default is FREE planning; --run is only for an already rented pod.
set -euo pipefail
REPO=${REPO:-$(cd "$(dirname "$0")/.." && pwd)}
OUT=${OUT:-/root/out/stage_b_pilot}
if [ "${1:---plan}" = --plan ]; then exec python3 "$REPO/stage_b/pilot_tools.py" plan; fi
[ "${1:-}" = --run ] || { echo 'FAILED: use --plan or --run'; exit 64; }
[ -n "${RUNPOD_POD_ID:-}" ] || { echo 'FAILED: --run is only for a RunPod pod'; exit 64; }
mkdir -p "$OUT"
exec >> "$OUT/runner.log" 2>&1
log(){ echo "$(date -u +%FT%TZ) $*"; }
GUARD_PID=${PILOT_GUARD_PID:-}
[ -n "$GUARD_PID" ] && kill -0 "$GUARD_PID" && [ -f "$OUT/guard_ready.json" ] \
  || { log 'FAILED: pod-side guard must be armed before setup'; exit 65; }
export VLLM_USE_FLASHINFER_SAMPLER=0
export HF_HUB_DISABLE_TELEMETRY=1
export OPENAI_API_KEY=EMPTY
unset ANTHROPIC_API_KEY COHERE_API_KEY GOOGLE_API_KEY GEMINI_API_KEY
ABL=huihui-ai/Huihui-Qwen3.8-27B-abliterated
QWEN=Qwen/Qwen3.8-27B
GEMMA=google/gemma-4-26B-A4B-it
PY=/root/venv_pilot/bin/python
PIDS=()
finish(){
  rc=$?
  trap - EXIT
  for pid in "${PIDS[@]}"; do kill -- "-$pid" 2>/dev/null || true; done
  python3 - "$OUT" "$rc" <<'PY'
import hashlib,json,pathlib,sys,tarfile
out=pathlib.Path(sys.argv[1]); rc=int(sys.argv[2])
(out/'finished.json').write_text(json.dumps({'exit_code':rc,'complete':rc==0})+'\n')
archive=out/'stage_b_pilot.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for path in sorted(out.iterdir()):
  if path.name not in (archive.name,'archive.sha256'):
   tar.add(path,arcname=path.name,recursive=True)
(out/'archive.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'\n')
PY
  # Do not kill the independent guard. The laptop watcher downloads and terminates early;
  # if it disappears, the guard still deletes the pod at its creation-based deadline.
  exit "$rc"
}
trap finish EXIT
check_time(){
  [ ! -f "$OUT/STOP_REQUESTED" ] && kill -0 "$GUARD_PID" \
    || { log 'FAILED: budget deadline or guard failure'; exit 66; }
}
log 'setup: frozen small pilot; no external model APIs'
check_time
python3 "$REPO/stage_b/pilot_tools.py" check
pip install -q 'vllm==0.33.0' > "$OUT/pip_vllm.log" 2>&1
python3 -m venv /root/venv_pilot
/root/venv_pilot/bin/pip install -q 'agentdojo==0.1.35' 'openai==3.52.0' > "$OUT/pip_agentdojo.log" 2>&1
"$PY" "$REPO/stage_b/select_pilot_cases.py" --check
"$PY" "$REPO/stage_b/test_harness.py" > "$OUT/offline_tests.log" 2>&1
"$PY" "$REPO/stage_b/test_pilot.py" >> "$OUT/offline_tests.log" 2>&1
python3 - <<'PY'
from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionRequest
assert 'thinking_token_budget' in ChatCompletionRequest.model_fields, 'unsupported thinking-budget API'
PY
cp "$REPO"/stage_b/pilot_{config,models,freeze}.json "$OUT/"
cp "$REPO/stage_b/cases_pilot.json" "$OUT/"
pip freeze > "$OUT/serving_packages.txt"
/root/venv_pilot/bin/pip freeze > "$OUT/benchmark_packages.txt"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader > "$OUT/gpu.txt"
toolcheck(){
  python3 - "$1" "$2" "$3" > "$OUT/toolcheck_${1}_$(echo "$2" | tr / _).json" <<'PY'
import json,sys,urllib.request
port,model,thinking=sys.argv[1],sys.argv[2],int(sys.argv[3])
body={'model':model,'temperature':0,'max_tokens':4096,'thinking_token_budget':thinking,
      'messages':[{'role':'user','content':'Use the get_weather tool for Paris.'}],
      'tools':[{'type':'function','function':{'name':'get_weather','description':'Weather for a city',
      'parameters':{'type':'object','properties':{'city':{'type':'string'}},'required':['city']}}}]}
req=urllib.request.Request(f'http://127.0.0.1:{port}/v1/chat/completions',data=json.dumps(body).encode(),
                           headers={'Content-Type':'application/json'})
data=json.load(urllib.request.urlopen(req,timeout=120)); choice=data['choices'][0]
calls=choice['message'].get('tool_calls') or []
assert choice['finish_reason']!='length', 'tool check exhausted generation cap'
assert calls and calls[0]['function']['name']=='get_weather', 'no parsed tool call'
assert isinstance(json.loads(calls[0]['function']['arguments']).get('city'),str)
print(json.dumps({'parsed_tool_call':True,'finish_reason':choice['finish_reason'],
                  'requested_thinking_budget':thinking,'usage':data.get('usage')}))
PY
}
serve(){
  check_time
  model=$1; port=$2; memory=$3
  revision=$(python3 -c "import json; print(json.load(open('$REPO/stage_b/pilot_models.json'))['$model']['revision'])")
  if [ "$model" = "$GEMMA" ]; then tool=gemma4; reasoning=gemma4; mm='{"image":0}'; think=512
  else tool=qwen3_coder; reasoning=qwen3; mm='{"image":0,"video":0}'; think=1024; fi
  log "serve $model on $port"
  setsid vllm serve "$model" --revision "$revision" --served-model-name "$model" --host 127.0.0.1 \
    --port "$port" --quantization fp8 --max-model-len 32768 --max-num-seqs 4 \
    --gpu-memory-utilization "$memory" --limit-mm-per-prompt "$mm" \
    --enable-auto-tool-choice --tool-call-parser "$tool" --reasoning-parser "$reasoning" \
    > "$OUT/serve_${port}_$(echo "$model" | tr / _).log" 2>&1 </dev/null &
  pid=$!; PIDS+=("$pid"); printf '%s' "$pid" > "$OUT/pid_$port"
  for i in $(seq 1 240); do
    check_time
    kill -0 "$pid" 2>/dev/null || { log "FAILED: server exited $model"; exit 67; }
    if curl -sf -m 3 "http://127.0.0.1:$port/v1/models" > "$OUT/models_${port}_$(echo "$model" | tr / _).json"; then
      toolcheck "$port" "$model" "$think"
      log "server and bounded-thinking tool check passed: $model"
      return
    fi
    sleep 3
  done
  log "FAILED: server startup timed out $model"; exit 68
}
stop_server(){
  local pid; pid=$(cat "$OUT/pid_$1")
  kill -- "-$pid" 2>/dev/null || true
  sleep 8
  kill -KILL -- "-$pid" 2>/dev/null || true
  sleep 2
}
ids(){ python3 -c "import json; print(','.join(json.load(open('$REPO/stage_b/cases_pilot.json'))['$1']))"; }
H(){
  check_time
  phase=$1; shift
  mkdir -p "$OUT/$phase"
  "$PY" "$REPO/stage_b/harness.py" --cases-file "$REPO/stage_b/cases_pilot.json" \
    --workers 2 --campaigns 1 --budget 3 --attacker-max-tokens 4096 --target-max-tokens 4096 \
    --attacker-thinking-budget 1024 --target-thinking-budget 512 --request-timeout 120 \
    --stop-file "$OUT/STOP_REQUESTED" --out "$OUT/$phase" "$@" >> "$OUT/harness.log" 2>&1
}
capability(){
  local label=$1; local model=$2
  H "capability_$label" --split dev --case-ids "$(ids capability_case_ids)" --condition no_attack \
    --target-model "$model" --target-name Qwen --target-label "$label" \
    --target-url http://127.0.0.1:8600/v1 --target-thinking-budget 1024
  "$PY" "$REPO/stage_b/pilot_tools.py" capability \
    --file "$OUT/capability_$label/dev__no_attack__none__$label.jsonl" >> "$OUT/capability_checks.jsonl"
}
# Check BOTH attackers on benign multi-step development tasks before held-out collection.
serve "$ABL" 8600 0.47; capability abliterated "$ABL"; stop_server 8600
serve "$QWEN" 8600 0.47; capability aligned "$QWEN"
serve "$GEMMA" 8500 0.45
H target_compatibility --split dev --case-ids "$(ids compatibility_case_ids)" --condition no_attack \
  --target-model "$GEMMA" --target-name Gemma --target-label gemma
python3 - "$OUT/target_compatibility/dev__no_attack__none__gemma.jsonl" <<'PY'
import json,sys
rows=[json.loads(l) for l in open(sys.argv[1])]
assert len(rows)==2 and any(r.get('episode',{}).get('utility') is True for r in rows), 'target not functional on development tasks'
assert all(not r.get('episode',{}).get('bad_tool_args') for r in rows), 'target tool parsing failed'
PY
log 'benign capability and target checks passed; held-out pilot begins'
H runs --split test --condition no_attack --target-model "$GEMMA" --target-name Gemma --target-label gemma
H runs --split test --condition adaptive --target-model "$GEMMA" --target-name Gemma --target-label gemma \
  --attacker-model "$QWEN" --attacker-label aligned --attacker-url http://127.0.0.1:8600/v1
stop_server 8600
serve "$ABL" 8600 0.47
H runs --split test --condition adaptive --target-model "$GEMMA" --target-name Gemma --target-label gemma \
  --attacker-model "$ABL" --attacker-label abliterated --attacker-url http://127.0.0.1:8600/v1
"$PY" "$REPO/stage_b/pilot_tools.py" summary --out "$OUT" > "$OUT/summary_printed.txt"
log ALL_DONE
