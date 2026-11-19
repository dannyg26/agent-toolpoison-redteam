#!/bin/bash
# CTF v2 pod-side driver for ONE arm: install vLLM, download the pinned checkpoint, serve it on loopback.
# Started detached by launch_v2.py after the guard is armed. Writes /root/out/v2/progress.log.
# The base-tokenizer fallback is used ONLY if the first server process EXITS before it ever becomes
# healthy (load failure). If it is still alive when the load wait times out, it is killed and the driver
# logs "serve FAILED (timeout)" and exits; no second server is started (R2-09). Liveness is checked with
# `ps -o stat=` (a zombie counts as dead), and each server runs in its own process group (setsid) so a
# stop kills the whole group and frees GPU memory and port 8000.
# Functions are defined first; main runs only when executed (test_v2.py sources this file with fakes).
set -u
ARM="${1:-}"
ROOT=/root/stage_e
OUT="${V2_OUT:-/root/out/v2}"
WAIT_TRIES="${WAIT_TRIES:-240}"
WAIT_PAUSE="${WAIT_PAUSE:-5}"

log() { echo "$(date -u +%FT%TZ) $*" >> "$OUT/progress.log"; }

serve() {  # extra args (tokenizer fallback) passed through; prints the server PID (= its process group)
  HF_HUB_OFFLINE=1 setsid python3 -m vllm.entrypoints.openai.api_server --model "$MODEL" --revision "$REVISION" \
    --served-model-name "csc-$ARM" --quantization fp8 --max-model-len 32768 --max-num-seqs 4 \
    --gpu-memory-utilization 0.90 --enable-auto-tool-choice --tool-call-parser qwen3_coder \
    --reasoning-parser qwen3 --host 127.0.0.1 --port 8000 --seed 20261118 "$@" >> "$OUT/vllm.log" 2>&1 &
  echo $!
}
healthy() { curl -sf --max-time 5 http://127.0.0.1:8000/v1/models | grep -q "csc-$ARM"; }
alive() {  # $1 = pid; false if gone or a zombie
  local st
  st=$(ps -o stat= -p "$1" 2>/dev/null) || return 1
  [ -n "$st" ] && [ "${st#Z}" = "$st" ]
}
wait_up() {  # $1 = pid; returns 0 healthy, 1 process died before healthy, 2 timeout with process alive
  local i
  for i in $(seq 1 "$WAIT_TRIES"); do
    healthy && return 0
    alive "$1" || return 1
    sleep "$WAIT_PAUSE"
  done
  healthy && return 0
  alive "$1" || return 1
  return 2
}
stop_server() {  # $1 = pid / process group; TERM, then KILL after 30 s
  local i
  kill -TERM -- "-$1" 2>/dev/null || kill -TERM "$1" 2>/dev/null
  for i in $(seq 1 30); do alive "$1" || return 0; sleep 1; done
  kill -KILL -- "-$1" 2>/dev/null || kill -KILL "$1" 2>/dev/null
  sleep 2
}
fetch_base_tokenizer() {
  python3 -c "from huggingface_hub import snapshot_download; snapshot_download('$BASE', revision='$BASE_REV', allow_patterns=['*.json','*.txt','*.jinja','*.model'])" \
      >> "$OUT/download.log" 2>&1
}
start_server() {  # sets PID; returns 0 when serving, 1 on failure (already logged)
  local rc
  PID=$(serve)
  wait_up "$PID"; rc=$?
  if [ "$rc" -eq 0 ]; then log "SERVING $ARM"; return 0; fi
  if [ "$rc" -eq 2 ]; then log "serve FAILED (timeout)"; stop_server "$PID"; return 1; fi
  log "server exited before becoming healthy; retry with base tokenizer"
  stop_server "$PID"
  fetch_base_tokenizer
  PID=$(serve --tokenizer "$BASE" --tokenizer-revision "$BASE_REV")
  wait_up "$PID"; rc=$?
  if [ "$rc" -eq 0 ]; then log "SERVING $ARM (base tokenizer)"; return 0; fi
  if [ "$rc" -eq 2 ]; then log "serve FAILED (timeout)"; else log "serve FAILED"; fi
  stop_server "$PID"
  return 1
}
record_provenance() {  # tokenizer/chat-template hashes of the served revision and the GPU/driver (R2-10, R2-22)
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader > "$OUT/nvidia-smi.txt" 2>&1
  python3 - "$MODEL" "$REVISION" "$BASE" "$BASE_REV" > "$OUT/tokenizer_hashes.json" 2>> "$OUT/download.log" <<'PY'
import hashlib, json, os, sys
from huggingface_hub import snapshot_download
out = {}
for label, repo, rev in (('served', sys.argv[1], sys.argv[2]), ('base', sys.argv[3], sys.argv[4])):
    try:
        path = snapshot_download(repo, revision=rev, local_files_only=True)
    except Exception as error:
        out[label] = {'repo': repo, 'error': type(error).__name__}
        continue
    files = {}
    for name in ('tokenizer_config.json', 'chat_template.jinja', 'tokenizer.json', 'generation_config.json'):
        p = os.path.join(path, name)
        if os.path.isfile(p):
            files[name] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    out[label] = {'repo': repo, 'revision': rev, 'sha256': files}
print(json.dumps(out))
PY
  log "provenance recorded"
}

main() {
  mkdir -p "$OUT"
  trap 'log "DRIVER_EXIT $?"' EXIT
  export PIP_BREAK_SYSTEM_PACKAGES=1 HF_HUB_ENABLE_HF_TRANSFER=1
  cd "$ROOT" || exit 1

  log "install start"
  python3 -m pip install -q vllm==0.33.0 hf_transfer >> "$OUT/install.log" 2>&1 || { log "install FAILED"; exit 1; }
  python3 -m pip freeze > "$OUT/pip-freeze.txt" 2>/dev/null
  log "install done"

  read -r MODEL REVISION BASE BASE_REV < <(python3 -c "
import json,sys; c=json.load(open('v2_config.json')); a=c['arms'][sys.argv[1]]; b=c['arms']['aligned']
print(a['model'], a['revision'], b['model'], b['revision'])" "$ARM")
  log "download start $MODEL"
  python3 -c "from huggingface_hub import snapshot_download; snapshot_download('$MODEL', revision='$REVISION')" \
      >> "$OUT/download.log" 2>&1 || { log "download FAILED"; exit 1; }
  log "download done"

  start_server || exit 1
  record_provenance
  while alive "$PID"; do sleep 15; echo "$(date -u +%FT%TZ)" > "$OUT/heartbeat"; done
  log "server exited"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
