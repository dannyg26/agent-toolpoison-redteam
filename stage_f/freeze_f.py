"""Write or verify the stage F freeze. Valid only once its commit is pushed (both launchers check).

Covers: stage_f sources/config/protocol; every reused file from stages B-E that F1/F2 execute or depend on;
the F1 item list and manifest; the passing F2 environment check; and the CTF v2 freeze, which must still
verify because F2 runs on the v2 sandbox, agent image and private cache.
Usage: python3 freeze_f.py write | check
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CACHE = Path('/home/capstone-study/stage_f')
REUSED = ['stage_b/pod_guard.py', 'sr_judge.py', 'judge_templates.json', 'stage_c/launch_ctf.py',
          'stage_c/endpoint_client.py', 'stage_c/environment.py', 'stage_c/trajectory.py', 'stage_c/guard_adapter.py',
          'stage_c/budget.py', 'stage_c/analyze_ctf.py', 'stage_d/score_run1.py', 'stage_e/trajectory_v2.py',
          'stage_e/environment_v2.py', 'stage_e/launch_v2.py', 'stage_e/v2_pod.sh', 'stage_e/v2_config.json',
          'stage_e/v2_freeze.json', 'stage_e/freeze_v2.py']


def text_hash(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def sources():
    return sorted(p.name for p in HERE.iterdir() if p.suffix in ('.py', '.sh', '.json', '.md')
                  and p.name != 'f_freeze.json' and not p.name.startswith('F-EXECUTION'))


def v2_still_verifies():
    sys.path.insert(0, str(HERE.parent/'stage_e'))
    from freeze_v2 import verify
    verify(json.loads((HERE.parent/'stage_e/v2_freeze.json').read_text()))
    return True


def f2_environment_check():
    report = json.loads((CACHE/'f2_environment_check.json').read_text())
    planned = json.loads((HERE/'f_config.json').read_text())['f2']['tasks']
    if not report.get('all_ok') or sorted(report['tasks']) != sorted(planned):
        raise ValueError('F2 environment check must pass for exactly the planned tasks')
    return hashlib.sha256((CACHE/'f2_environment_check.json').read_bytes()).hexdigest()


def snapshot():
    manifest = json.loads((CACHE/'items_f1_manifest.json').read_text())
    if hashlib.sha256((CACHE/'items_f1.jsonl').read_bytes()).hexdigest() != manifest['sha256']:
        raise ValueError('F1 items do not match their manifest')
    return {'study': 'stage F',
            'sha256': {n: text_hash(HERE/n) for n in sources()},
            'reused_sha256': {n: text_hash(HERE.parent/n) for n in REUSED},
            'items_f1_sha256': manifest['sha256'],
            'f2_environment_check_sha256': f2_environment_check(),
            'v2_freeze_verifies': v2_still_verifies()}


def verify(value):
    if not value.get('externally_timestamped_before_collection'):
        raise PermissionError('Not a pushed pre-collection freeze')
    current = snapshot()
    for key in ('sha256', 'reused_sha256', 'items_f1_sha256', 'f2_environment_check_sha256', 'v2_freeze_verifies'):
        if value.get(key) != current[key]:
            changed = (sorted(k for k in set(value[key]) | set(current[key]) if value[key].get(k) != current[key].get(k))
                       if isinstance(current[key], dict) else [key])
            raise ValueError('Frozen stage F content changed: %s %s' % (key, changed))


def check_frozen_and_pushed():
    """Shared by launch_f1/launch_f2: freeze verifies, stage_f is clean, and HEAD is on a remote branch."""
    verify(json.loads((HERE/'f_freeze.json').read_text()))
    git = ['git', '-c', 'safe.directory=*', '-C', str(HERE)]
    if subprocess.run(git+['status', '--porcelain', '--', '.'], capture_output=True, text=True, check=True).stdout.strip():
        raise SystemExit('stage_f has uncommitted changes; commit and push the freeze first')
    head = subprocess.run(git+['rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    if not subprocess.run(git+['branch', '-r', '--contains', head], capture_output=True, text=True, check=True).stdout.strip():
        raise SystemExit('The frozen commit is not on any remote branch; push it before launch')
    return head


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if action == 'write':
        if not json.loads((HERE/'f_config.json').read_text()).get('allow_live_model_calls'):
            raise SystemExit('Freeze requires the collection configuration')
        value = dict(snapshot(), prepared_at=datetime.now(timezone.utc).isoformat(),
                     status='collection freeze; counts only once its commit is pushed',
                     externally_timestamped_before_collection=True)
        (HERE/'f_freeze.json').write_text(json.dumps(value, indent=1)+'\n')
        verify(value)
        print('stage F freeze written and verified; commit and push before launch')
    elif action == 'dry-run':
        print(json.dumps({k: (len(v) if isinstance(v, dict) else v) for k, v in snapshot().items()}, indent=1))
    else:
        verify(json.loads((HERE/'f_freeze.json').read_text()))
        print('stage F freeze verifies')
