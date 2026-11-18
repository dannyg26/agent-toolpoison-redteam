#!/bin/bash
# Held-out comparison runner (HELDOUT-PROTOCOL.md). Default is FREE planning; --run is only for the rented pod,
# started by bootstrap_heldout.py after the pod-side guard is armed AND its deadline verified.
# Run order (counterbalanced, block membership frozen in cases_heldout.json):
#   abliterated: capability -> Gemma: compatibility, clean, fixed -> block1 abliterated
#   -> aligned: capability, block1 aligned, block2 aligned -> abliterated (warm reload): block2 abliterated
set -euo pipefail
REPO=${REPO:-$(cd "$(dirname "$0")/.." && pwd)}
OUT=${OUT:-/root/out/stage_b_heldout}
if [ "${1:---plan}" = --plan ]; then python3 "$REPO/stage_b/heldout_tools.py" plan; exec python3 "$REPO/stage_b/heldout_tools.py" cost; fi
[ "${1:-}" = --run ] || { echo 'FAILED: use --plan or --run'; exit 64; }
[ -n "${RUNPOD_POD_ID:-}" ] || { echo 'FAILED: --run is only for a RunPod pod'; exit 64; }
mkdir -p "$OUT"
exec >> "$OUT/runner.log" 2>&1
log(){ echo "$(date -u +%FT%TZ) $*"; }
GUARD_PID=${HELDOUT_GUARD_PID:-}
[ -n "$GUARD_PID" ] && kill -0 "$GUARD_PID" && [ -f "$OUT/guard_ready.json" ] && [ -f "$OUT/guard_verified.json" ] \
  || { log 'FAILED: verified pod-side guard must be armed before setup'; exit 65; }
export VLLM_USE_FLASHINFER_SAMPLER=0 HF_HUB_DISABLE_TELEMETRY=1 OPENAI_API_KEY=EMPTY
unset ANTHROPIC_API_KEY COHERE_API_KEY GOOGLE_API_KEY GEMINI_API_KEY
cfg(){ python3 -c "import json,sys; print(json.load(open('$REPO/stage_b/heldout_config.json'))[sys.argv[1]])" "$1"; }
ABL=$(cfg main_attacker); QWEN=$(cfg control_attacker); GEMMA=$(cfg target)
WORKERS=$(cfg workers); SEQS=$(cfg max_num_seqs); BUDGET=$(cfg candidate_budget); TIMEOUT=$(cfg request_timeout_seconds)
AMAX=$(cfg attacker_max_tokens); ATHINK=$(cfg attacker_thinking_budget); TMAX=$(cfg target_max_tokens)
TTHINK=$(cfg target_thinking_budget); CTHINK=$(cfg capability_thinking_budget); MAXERR=$(cfg harness_max_error_rate)
CTX=$(cfg context_length); AMEM=$(cfg attacker_gpu_memory_utilization); TMEM=$(cfg target_gpu_memory_utilization)
PY=/root/venv_heldout/bin/python
SOFTSEC=$(cfg soft_stop_seconds_before_deadline); GRACE=$(cfg supervisor_grace_seconds)
SOFT=$(python3 "$REPO/stage_b/heldout_runtime.py" soft-stop-epoch --ready "$OUT/guard_ready.json" --soft-stop-seconds "$SOFTSEC")
# Soft stop: deadline - 5 min. The timer creates STOP_REQUESTED then; heldout_runtime also enforces it per request.
python3 "$REPO/stage_b/heldout_runtime.py" timer --ready "$OUT/guard_ready.json" --stop-file "$OUT/STOP_REQUESTED" \
  --soft-stop-seconds "$SOFTSEC" >> "$OUT/soft_stop_timer.log" 2>&1 &
TIMER_PID=$!
PIDS=()
finish(){
  rc=$?
  trap - EXIT
  for pid in "${PIDS[@]}"; do kill -- "-$pid" 2>/dev/null || true; done
  kill "$TIMER_PID" 2>/dev/null || true
  # Planned-inventory report on EVERY exit path (complete, failed or deadline); never blocks archiving.
  [ -x "$PY" ] && timeout 60 "$PY" "$REPO/stage_b/analyze_heldout.py" report --download "$OUT" \
    --output "$OUT/heldout_summary.json" > "$OUT/summary_printed.txt" 2>&1 || true
  python3 - "$OUT" "$rc" <<'PY'
import hashlib,json,pathlib,sys,tarfile
out=pathlib.Path(sys.argv[1]); rc=int(sys.argv[2])
(out/'finished.json').write_text(json.dumps({'exit_code':rc,'complete':rc==0})+'\n')
archive=out/'stage_b_heldout.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for path in sorted(out.iterdir()):
  if path.name not in (archive.name,'archive.sha256'):
   tar.add(path,arcname=path.name,recursive=True)
(out/'archive.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'\n')
PY
  exit "$rc"     # the independent guard is never killed here
}
trap finish EXIT
check_time(){ [ ! -f "$OUT/STOP_REQUESTED" ] && [ "$(date +%s)" -lt "$SOFT" ] && kill -0 "$GUARD_PID" \
  || { log 'FAILED: soft stop, budget deadline or guard failure'; exit 66; }; }
log 'setup: held-out comparison; no external model APIs'
check_time
python3 "$REPO/stage_b/heldout_tools.py" check
pip install -q 'vllm==0.33.0' > "$OUT/pip_vllm.log" 2>&1
python3 -m venv /root/venv_heldout
/root/venv_heldout/bin/pip install -q 'agentdojo==0.1.35' 'openai==3.52.0' > "$OUT/pip_agentdojo.log" 2>&1
"$PY" "$REPO/stage_b/select_heldout_cases.py" --check
"$PY" "$REPO/stage_b/test_harness.py" > "$OUT/offline_tests.log" 2>&1
"$PY" "$REPO/stage_b/test_heldout.py" >> "$OUT/offline_tests.log" 2>&1
python3 - <<'PY'
from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionRequest
assert 'thinking_token_budget' in ChatCompletionRequest.model_fields, 'unsupported thinking-budget API'
PY
cp "$REPO"/stage_b/{heldout_config,pilot_models,heldout_freeze,cases_heldout}.json "$OUT/"
pip freeze > "$OUT/serving_packages.txt"
/root/venv_heldout/bin/pip freeze > "$OUT/benchmark_packages.txt"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader > "$OUT/gpu.txt"
toolcheck(){
  # Elapsed-time bound enforced by the OS (GNU timeout), not by socket timeouts: killed at the soft stop.
  local left=$(( SOFT - $(date +%s) ))
  [ "$left" -gt 1 ] || { log 'FAILED: soft stop reached before tool check'; exit 66; }
  timeout --kill-after=5 "$left" python3 - "$1" "$2" "$3" "$SOFT" > "$OUT/toolcheck_${1}_$(echo "$2" | tr / _).json" <<'PY'
import json,sys,time,urllib.request
port,model,thinking=sys.argv[1],sys.argv[2],int(sys.argv[3])
left=float(sys.argv[4])-time.time()
assert left>1, 'soft stop reached before tool check'
body={'model':model,'temperature':0,'max_tokens':4096,'thinking_token_budget':thinking,
      'messages':[{'role':'user','content':'Use the get_weather tool for Paris.'}],
      'tools':[{'type':'function','function':{'name':'get_weather','description':'Weather for a city',
      'parameters':{'type':'object','properties':{'city':{'type':'string'}},'required':['city']}}}]}
req=urllib.request.Request(f'http://127.0.0.1:{port}/v1/chat/completions',data=json.dumps(body).encode(),
                           headers={'Content-Type':'application/json'})
data=json.load(urllib.request.urlopen(req,timeout=min(300,left))); choice=data['choices'][0]
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
  if [ "$model" = "$GEMMA" ]; then tool=gemma4; reasoning=gemma4; mm='{"image":0}'; think=$TTHINK
  else tool=qwen3_coder; reasoning=qwen3; mm='{"image":0,"video":0}'; think=$ATHINK; fi
  log "serve $model on $port"
  setsid vllm serve "$model" --revision "$revision" --served-model-name "$model" --host 127.0.0.1 \
    --port "$port" --quantization fp8 --max-model-len "$CTX" --max-num-seqs "$SEQS" \
    --gpu-memory-utilization "$memory" --limit-mm-per-prompt "$mm" \
    --enable-auto-tool-choice --tool-call-parser "$tool" --reasoning-parser "$reasoning" \
    > "$OUT/serve_${port}_$(echo "$model" | tr / _)_$(date +%s).log" 2>&1 </dev/null &
  pid=$!; PIDS+=("$pid"); printf '%s' "$pid" > "$OUT/pid_$port"
  for i in $(seq 1 400); do
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
  kill -- "-$pid" 2>/dev/null || true; sleep 8; kill -KILL -- "-$pid" 2>/dev/null || true; sleep 2
}
ids(){ python3 -c "import json; d=json.load(open('$REPO/stage_b/cases_heldout.json')); v=d['blocks'].get('$1', d.get('$1')); print(','.join(v))"; }
H(){
  check_time
  dir=$1; shift
  mkdir -p "$OUT/$dir"
  log "phase $dir: $*"
  # Each phase is a supervised child process, killed at soft stop + GRACE s; this runner survives to report.
  "$PY" "$REPO/stage_b/heldout_runtime.py" supervise --ready "$OUT/guard_ready.json" --soft-stop-seconds "$SOFTSEC" \
    --grace-seconds "$GRACE" --events "$OUT/supervisor_events.jsonl" -- \
    --cases-file "$REPO/stage_b/cases_heldout.json" \
    --workers "$WORKERS" --campaigns 1 --budget "$BUDGET" --attacker-max-tokens "$AMAX" --target-max-tokens "$TMAX" \
    --attacker-thinking-budget "$ATHINK" --target-thinking-budget "$TTHINK" --request-timeout "$TIMEOUT" \
    --max-error-rate "$MAXERR" --stop-file "$OUT/STOP_REQUESTED" --out "$OUT/$dir" "$@" >> "$OUT/harness.log" 2>&1
}
capability(){ # label model
  H "capability_$1" --split dev --case-ids "$(ids capability_case_ids)" --condition no_attack \
    --target-model "$2" --target-name Qwen --target-label "$1" --target-url http://127.0.0.1:8600/v1 \
    --target-thinking-budget "$CTHINK"
  "$PY" "$REPO/stage_b/heldout_tools.py" capability \
    --file "$OUT/capability_$1/dev__no_attack__none__$1.jsonl" >> "$OUT/capability_checks.jsonl"
}
arm(){ # block label model
  H "runs_$1" --split test --case-ids "$(ids "$1")" --condition adaptive --target-model "$GEMMA" \
    --target-name "$(cfg target_name)" --target-label gemma --attacker-model "$3" --attacker-label "$2" \
    --attacker-url http://127.0.0.1:8600/v1
}
A=http://127.0.0.1:8600/v1
serve "$ABL" 8600 "$AMEM"
capability abliterated "$ABL"
serve "$GEMMA" 8500 "$TMEM"
H target_compatibility --split dev --case-ids "$(ids compatibility_case_ids)" --condition no_attack \
  --target-model "$GEMMA" --target-name Gemma --target-label gemma
python3 - "$OUT/target_compatibility/dev__no_attack__none__gemma.jsonl" <<'PY'
import json,sys
rows=[json.loads(l) for l in open(sys.argv[1])]
assert len(rows)==2 and any(r.get('episode',{}).get('utility') is True for r in rows), 'target not functional on development tasks'
assert all(not r.get('episode',{}).get('bad_tool_args') for r in rows), 'target tool parsing failed'
PY
H baselines --split test --condition no_attack --target-model "$GEMMA" --target-name Gemma --target-label gemma
H baselines --split test --condition fixed --target-model "$GEMMA" --target-name Gemma --target-label gemma
log 'benign checks and baselines done; held-out attack collection begins'
arm block1 abliterated "$ABL"
stop_server 8600
serve "$QWEN" 8600 "$AMEM"
capability aligned "$QWEN"
arm block1 aligned "$QWEN"
arm block2 aligned "$QWEN"
stop_server 8600
serve "$ABL" 8600 "$AMEM"
arm block2 abliterated "$ABL"
log ALL_DONE     # the planned-inventory report is written by finish() on this and every other exit path
