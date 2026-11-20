#!/bin/bash
# F1 pod-side driver: install, then for each arm in order: download, generate, judge, free the checkpoint.
# Each arm's answers and judge scores are written as soon as they exist (the launcher fetches them as it
# goes), so a stop loses at most the arm in progress. Started detached by launch_f1.py after the guard arms.
set -u
ROOT=/root/stage_f
OUT=/root/out/f1
mkdir -p "$OUT"
log() { echo "$(date -u +%FT%TZ) $*" >> "$OUT/progress.log"; }
trap 'log "DRIVER_EXIT $?"' EXIT
export PIP_BREAK_SYSTEM_PACKAGES=1 HF_HUB_ENABLE_HF_TRANSFER=1
cd "$ROOT" || exit 1

log "install start"
python3 -m pip install -q vllm==0.33.0 hf_transfer peft >> "$OUT/install.log" 2>&1 || { log "install FAILED"; exit 1; }
python3 -m pip freeze > "$OUT/pip-freeze.txt" 2>/dev/null
log "install done"

ARMS=$(python3 -c "import json; print(' '.join(json.load(open('f_config.json'))['arm_order']))")
for ARM in $ARMS; do
  log "download start $ARM"
  python3 - "$ARM" >> "$OUT/download.log" 2>&1 <<'PY' || { log "download FAILED $ARM"; continue; }
import json, sys
from huggingface_hub import snapshot_download
a = json.load(open('v2_config.json'))['arms'][sys.argv[1]]
snapshot_download(a['model'], revision=a['revision'])
PY
  log "generate start $ARM"
  if HF_HUB_OFFLINE=1 python3 pod_f1.py generate --arm "$ARM" >> "$OUT/generate-$ARM.log" 2>&1; then
    log "generate done $ARM"
    if python3 pod_f1.py judge --arm "$ARM" >> "$OUT/judge-$ARM.log" 2>&1; then log "judge done $ARM"; else log "judge FAILED $ARM"; fi
  else
    log "generate FAILED $ARM"
  fi
  python3 - "$ARM" >> "$OUT/download.log" 2>&1 <<'PY'
import json, sys
from huggingface_hub import scan_cache_dir
repo = json.load(open('v2_config.json'))['arms'][sys.argv[1]]['model']
info = scan_cache_dir()
hashes = [rev.commit_hash for r in info.repos if r.repo_id == repo for rev in r.revisions]
if hashes:
    info.delete_revisions(*hashes).execute()
PY
  log "freed $ARM ($(df -h /root | tail -1 | awk '{print $4}') free)"
done
log "ALL_DONE"
