"""Verify that the stage D run 1 freeze differs from the working tree ONLY by the documented changes.

REVIEW-001 / REPAIR-001. `freeze_run1.py check` fails after the repair by design, because the repair
(a) fixes a pre-scoring bug in score_run1.py and adds regression tests to test_run1.py (D-01, D-02), and
(b) adds unfrozen documents to stage_d/, which freeze_run1.sources() picks up by suffix. This script
checks that every other frozen hash (sources, reused files, private artefacts, items, runner image)
still matches run1_freeze.json, and that the two edited files are exactly the documented repair: their
versions before the repair commit (97f850f^) match the frozen hashes, and the working-tree versions equal
the repair commit's blobs (97f850f), so nothing changed after the repair.

REVIEW-007 R7-02 / D-31: EXPANDED-STUDY-PLAN.md, also hashed in run1_freeze.json, had a "Decision update"
section appended in commit 418edc1 after the freeze. It is accepted here only as an append: its version
before that commit (418edc1^) must match the frozen hash, and the working tree must start with those bytes.
(Before REVIEW-007 this script compared the committed files with the frozen hashes, which held only until
the repair was committed in 97f850f.)

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

REPAIRED = {'score_run1.py': '97f850f', 'test_run1.py': '97f850f'}  # D-01, D-02: file -> repair commit
APPENDED = {'EXPANDED-STUDY-PLAN.md': '418edc1'}  # D-31: file -> commit that appended to it
EXPECTED_MODIFIED = set(REPAIRED) | set(APPENDED)
EXPECTED_ADDED = {'RUN1-EXECUTION-LOG.md', 'DEVIATIONS-AND-LIMITATIONS.md', 'FOLLOWUP-DESIGN.md'}


def git_blob(rev, name):
    out = subprocess.run(['git', '-c', 'safe.directory=*', 'show', '%s:stage_d/%s' % (rev, name)], cwd=ROOT,
                         capture_output=True, check=True).stdout
    return out.replace(b'\r\n', b'\n')


def working(name):
    return (ROOT/'stage_d'/name).read_bytes().replace(b'\r\n', b'\n')


def sha(data):
    return hashlib.sha256(data).hexdigest()


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
    for name, commit in sorted(REPAIRED.items()):
        if sha(git_blob(commit + '^', name)) != frozen['sha256'][name]:
            problems.append('%s before %s does not match its frozen hash' % (name, commit))
        if working(name) != git_blob(commit, name):
            problems.append('%s differs from its repaired version in %s' % (name, commit))
    for name, commit in sorted(APPENDED.items()):
        before = git_blob(commit + '^', name)
        if sha(before) != frozen['sha256'][name]:
            problems.append('%s before %s does not match its frozen hash' % (name, commit))
        if not working(name).startswith(before):
            problems.append('%s is not an append to its frozen version' % name)
    if problems:
        raise SystemExit('FREEZE DELTA NOT AS DOCUMENTED: ' + '; '.join(problems))
    print('freeze delta as documented: modified %s (repaired %s, appended %s); added %s; '
          'all other frozen hashes match' % (sorted(modified), sorted(REPAIRED), sorted(APPENDED), sorted(added)))


if __name__ == '__main__':
    main()
