#!/bin/bash
# CTF v2 pod-side driver for ONE arm: install vLLM, download the pinned checkpoint, serve it on loopback.
# Started detached by launch_v2.py after the guard is armed. Writes /root/out/v2/progress.log.
# The base-tokenizer fallback is used only if the server exits before it ever becomes healthy (load failure).
set -u
ARM="$1"
ROOT=/root/stage_e
OUT=/root/out/v2
mkdir -p "$OUT"
log() { echo "$(date -u +%FT%TZ) $*" >> "$OUT/progress.log"; }
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

serve() {  # extra args (tokenizer fallback) passed through
  HF_HUB_OFFLINE=1 python3 -m vllm.entrypoints.openai.api_server --model "$MODEL" --revision "$REVISION" \
    --served-model-name "csc-$ARM" --quantization fp8 --max-model-len 32768 --max-num-seqs 4 \
    --gpu-memory-utilization 0.90 --enable-auto-tool-choice --tool-call-parser qwen3_coder \
    --reasoning-parser qwen3 --host 127.0.0.1 --port 8000 --seed 20261118 "$@" >> "$OUT/vllm.log" 2>&1 &
  echo $!
}
healthy() { curl -sf --max-time 5 http://127.0.0.1:8000/v1/models | grep -q "csc-$ARM"; }
wait_up() {  # $1 = pid; returns 0 healthy, 1 process died
  for i in $(seq 1 240); do
    healthy && return 0
    kill -0 "$1" 2>/dev/null || return 1
    sleep 5
  done
  return 1
}

PID=$(serve)
if wait_up "$PID"; then
  log "SERVING $ARM"
else
  log "server load failed; retry with base tokenizer"
  python3 -c "from huggingface_hub import snapshot_download; snapshot_download('$BASE', revision='$BASE_REV', allow_patterns=['*.json','*.txt','*.jinja','*.model'])" \
      >> "$OUT/download.log" 2>&1
  PID=$(serve --tokenizer "$BASE" --tokenizer-revision "$BASE_REV")
  if wait_up "$PID"; then log "SERVING $ARM (base tokenizer)"; else log "serve FAILED"; exit 1; fi
fi
while kill -0 "$PID" 2>/dev/null; do sleep 15; echo "$(date -u +%FT%TZ)" > "$OUT/heartbeat"; done
log "server exited"
