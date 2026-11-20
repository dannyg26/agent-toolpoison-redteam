#!/bin/bash
# F1 pod-side driver: install, then for each arm in order: download, generate, judge, free the checkpoint.
# Each arm's answers and judge scores are written as soon as they exist (the launcher fetches them as it
# goes), so a stop loses at most the arm in progress. Started detached by launch_f1.py after the guard arms.
# The install is bounded (timeout 900 s) and retried once automatically after clearing the pip cache
# (logged "install RETRY"), because the v2 abliterated install stalled for about 33 min (R5-09).
# There is no tokenizer fallback: an arm whose checkpoint fails to load is lost and reported as such.
set -u
ROOT=/root/stage_f
OUT=/root/out/f1
INSTALL_TIMEOUT="${INSTALL_TIMEOUT:-900}"
mkdir -p "$OUT"
log() { echo "$(date -u +%FT%TZ) $*" >> "$OUT/progress.log"; }
install_once() { timeout "$INSTALL_TIMEOUT" python3 -m pip install -q vllm==0.33.0 hf_transfer peft==0.21.3 >> "$OUT/install.log" 2>&1; }
trap 'log "DRIVER_EXIT $?"' EXIT
export PIP_BREAK_SYSTEM_PACKAGES=1 HF_HUB_ENABLE_HF_TRANSFER=1
cd "$ROOT" || exit 1

log "install start"
if ! install_once; then
  log "install RETRY (first attempt failed or exceeded ${INSTALL_TIMEOUT}s)"
  python3 -m pip cache purge >> "$OUT/install.log" 2>&1
  install_once || { log "install FAILED"; exit 1; }
fi
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
    log "thinking check $ARM $(python3 -c "import json,sys; c=json.load(open(sys.argv[1])); print('closed %d/%d alert=%s' % (c['thinking_closed'], c['n'], c['alert']))" "$OUT/thinking_check_$ARM.jsonl" 2>&1)"
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
