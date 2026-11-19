"""Verify that the stage D run 1 freeze differs from the working tree ONLY by the documented repair.

REVIEW-001 / REPAIR-001. `freeze_run1.py check` fails after the repair by design, because the repair
(a) fixes a pre-scoring bug in score_run1.py and adds regression tests to test_run1.py (D-01, D-02), and
(b) adds unfrozen documents to stage_d/, which freeze_run1.sources() picks up by suffix. This script
checks that every other frozen hash (sources, reused files, private artefacts, items, runner image)
still matches run1_freeze.json, and that the two edited files' committed versions match their frozen hashes.

Run in WSL from the repository root:
  /home/capstone-study/stage_d/venv/bin/python reviews/check_freeze_delta.py
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'stage_d'))
import freeze_run1  # noqa: E402

EXPECTED_MODIFIED = {'score_run1.py', 'test_run1.py'}
EXPECTED_ADDED = {'RUN1-EXECUTION-LOG.md', 'DEVIATIONS-AND-LIMITATIONS.md', 'FOLLOWUP-DESIGN.md'}


def main():
    frozen = json.loads((ROOT/'stage_d/run1_freeze.json').read_text())
    current = freeze_run1.snapshot()
    problems = []
    for key in ('reused_sha256', 'private_sha256', 'items_sha256', 'cweval_runner_image'):
        if frozen[key] != current[key]:
            problems.append('%s changed' % key)
    names = set(frozen['sha256']) | set(current['sha256'])
    differing = {n for n in names if frozen['sha256'].get(n) != current['sha256'].get(n)}
    modified = {n for n in differing if n in frozen['sha256'] and n in current['sha256']}
    added = {n for n in differing if n not in frozen['sha256']}
    removed = {n for n in differing if n not in current['sha256']}
    if modified != EXPECTED_MODIFIED:
        problems.append('modified %s, expected %s' % (sorted(modified), sorted(EXPECTED_MODIFIED)))
    if not added <= EXPECTED_ADDED:
        problems.append('unexpected added files %s' % sorted(added - EXPECTED_ADDED))
    if removed:
        problems.append('removed frozen files %s' % sorted(removed))
    for name in sorted(EXPECTED_MODIFIED):
        blob = subprocess.run(['git', '-c', 'safe.directory=*', 'show', 'HEAD:stage_d/'+name], cwd=ROOT, capture_output=True, check=True).stdout
        if hashlib.sha256(blob.replace(b'\r\n', b'\n')).hexdigest() != frozen['sha256'][name]:
            problems.append('committed %s does not match its frozen hash' % name)
    if problems:
        raise SystemExit('FREEZE DELTA NOT AS DOCUMENTED: ' + '; '.join(problems))
    print('freeze delta as documented: modified %s; added %s; all other frozen hashes match'
          % (sorted(modified), sorted(added)))


if __name__ == '__main__':
    main()
