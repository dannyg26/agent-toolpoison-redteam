#!/bin/bash
# Stage D run 1, pod-side driver. Started detached by launch_run1.py after the guard is armed.
# Arms run in the frozen order, one process each. The next arm's checkpoint downloads while the current
# arm generates; each arm's checkpoint is deleted after use so at most two are on disk.
set -u
ROOT=/root/stage_d
OUT=/root/out/stage_d
mkdir -p "$OUT/generation" "$OUT/judge"
log() { echo "$(date -u +%FT%TZ) $*" >> "$OUT/progress.log"; }
export PIP_BREAK_SYSTEM_PACKAGES=1 HF_HUB_ENABLE_HF_TRANSFER=1
cd "$ROOT" || exit 1

log "install start"
python3 -m pip install -q vllm==0.33.0 hf_transfer peft >> "$OUT/install.log" 2>&1 || { log "install FAILED"; exit 1; }
log "install done"

ARMS=$(python3 -c "import json; print(' '.join(json.load(open('run1_config.json'))['arm_order']))")
download() {   # $1 = arm
  python3 - "$1" >> "$OUT/download-$1.log" 2>&1 <<'PY'
import json, sys
from huggingface_hub import snapshot_download
arm = json.load(open('run1_config.json'))['arms'][sys.argv[1]]
snapshot_download(arm['model'], revision=arm['revision'])
PY
}
cache_dir() {  # $1 = arm
  python3 -c "import json,sys; m=json.load(open('run1_config.json'))['arms'][sys.argv[1]]['model']; print('/root/.cache/huggingface/hub/models--'+m.replace('/','--'))" "$1"
}

set -- $ARMS
download "$1" && touch "$OUT/downloaded-$1" || log "download FAILED $1"
while [ $# -gt 0 ]; do
  ARM=$1; shift
  NEXT=${1:-}
  if [ -n "$NEXT" ]; then ( download "$NEXT" && touch "$OUT/downloaded-$NEXT" || log "download FAILED $NEXT" ) & fi
  if [ ! -e "$OUT/downloaded-$ARM" ]; then log "skip $ARM: not downloaded"; wait; continue; fi
  log "generate start $ARM"
  if HF_HUB_OFFLINE=1 python3 pod_generate.py --arm "$ARM" --items "$ROOT/items" --injec "$ROOT/injec" \
      --out "$OUT/generation" >> "$OUT/generate-$ARM.log" 2>&1; then
    log "generate done $ARM"
  elif [ ! -e "$OUT/generation/$ARM.jsonl" ]; then
    # Pre-registered fallback: the arm produced no output, so retry once with the base tokenizer files.
    log "generate retry $ARM with base tokenizer"
    python3 - >> "$OUT/download-tokenizer.log" 2>&1 <<'PY'
import json
from huggingface_hub import snapshot_download
base = json.load(open('run1_config.json'))['arms']['aligned']
snapshot_download(base['model'], revision=base['revision'], allow_patterns=['*.json', '*.txt', '*.jinja', '*.model'])
PY
    HF_HUB_OFFLINE=1 python3 pod_generate.py --arm "$ARM" --items "$ROOT/items" --injec "$ROOT/injec" \
        --out "$OUT/generation" --tokenizer-from-base >> "$OUT/generate-$ARM.log" 2>&1 \
        && log "generate done $ARM (base tokenizer)" || log "generate FAILED $ARM"
  else
    log "generate FAILED $ARM"
  fi
  rm -rf "$(cache_dir "$ARM")"
  wait
done

DONE=$(ls "$OUT"/generation/*.done 2>/dev/null | xargs -n1 basename 2>/dev/null | sed 's/\.done$//' | tr '\n' ' ')
log "judge start ($DONE)"
if [ -n "$DONE" ]; then
  python3 pod_judge.py --items "$ROOT/items" --gen "$OUT/generation" --out "$OUT/judge" --arms $DONE \
      >> "$OUT/judge.log" 2>&1 && log "judge done" || log "judge FAILED"
fi
log "ALL_DONE"
touch "$OUT/ALL_DONE"
