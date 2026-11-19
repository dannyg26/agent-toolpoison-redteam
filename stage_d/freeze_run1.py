"""Write or verify the stage D run 1 freeze. Valid only once its commit is pushed (the launcher checks).

Covers: stage_d sources, protocol and config; reused files from stages B and C; and private-cache artefacts
(dataset hashes, item lists, items manifest, CWEval harness check) plus the CWEval runner image ID.
Usage: python3 freeze_run1.py write | check
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CACHE = Path('/home/capstone-study/stage_d')
REUSED = ['sr_judge.py', 'judge_templates.json', 'stage_b/pod_guard.py', 'stage_c/launch_ctf.py',
          'stage_c/analyze_ctf.py', 'stage_c/guard_adapter.py', 'stage_c/budget.py', 'stage_c/environment.py']
PRIVATE = ['dataset_hashes.json', 'items_manifest.json', 'cweval_harness_check.json']


def text_hash(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def sources():
    names = sorted(p.name for p in HERE.iterdir() if p.suffix in ('.py', '.sh', '.json', '.md')
                   and p.name not in ('run1_freeze.json',))
    return names + ['cweval_runner/Dockerfile']


def image_id():
    return subprocess.run(['docker', 'image', 'inspect', 'capstone-cweval-runner:prepared', '--format', '{{.Id}}'],
                          capture_output=True, text=True, check=True).stdout.strip()


def snapshot():
    return {'study': 'stage D run 1',
            'sha256': {name: text_hash(HERE/name) for name in sources()},
            'reused_sha256': {name: text_hash(HERE.parent/name) for name in REUSED},
            'private_sha256': {name: hashlib.sha256((CACHE/name).read_bytes()).hexdigest() for name in PRIVATE},
            'items_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((CACHE/'items').glob('*.jsonl'))},
            'cweval_runner_image': image_id()}


def verify(value):
    if not value.get('externally_timestamped_before_collection'):
        raise PermissionError('Not a pushed pre-collection freeze')
    current = snapshot()
    for key in ('sha256', 'reused_sha256', 'private_sha256', 'items_sha256', 'cweval_runner_image'):
        if value[key] != current[key]:
            changed = sorted(k for k in set(value[key]) | set(current[key])
                             if value[key].get(k) != current[key].get(k)) if isinstance(current[key], dict) else [key]
            raise ValueError('Frozen run 1 content changed: %s %s' % (key, changed))
    manifest = json.loads((CACHE/'items_manifest.json').read_text())
    for name, entry in manifest.items():
        if value['items_sha256'][name+'.jsonl'] != entry['sha256']:
            raise ValueError('Item list does not match its manifest: '+name)


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if action == 'write':
        config = json.loads((HERE/'run1_config.json').read_text())
        if not config.get('allow_live_model_calls'):
            raise SystemExit('Freeze requires the collection configuration')
        value = dict(snapshot(), prepared_at=datetime.now(timezone.utc).isoformat(),
                     status='collection freeze; counts only once its commit is pushed',
                     externally_timestamped_before_collection=True)
        (HERE/'run1_freeze.json').write_text(json.dumps(value, indent=1)+'\n')
        verify(value)
        print('run 1 freeze written and verified; commit and push before launch')
    else:
        verify(json.loads((HERE/'run1_freeze.json').read_text()))
        print('run 1 freeze verifies')


if __name__ == '__main__':
    main()
