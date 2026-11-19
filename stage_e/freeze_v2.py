"""Write or verify the CTF v2 freeze. Valid only once its commit is pushed (launch_v2.py checks).

Covers stage_e sources/config/protocol, the reused stage B/C files, the stage C private cache artefacts the
v2 sandbox depends on (image lock, flag patches, resolved tasks), and the v2 agent image ID.
Usage: python3 freeze_v2.py write | check
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
STAGE_C_CACHE = Path('/home/capstone-study/stage_c')
REUSED = ['stage_b/pod_guard.py', 'stage_c/environment.py', 'stage_c/endpoint_client.py', 'stage_c/trajectory.py',
          'stage_c/launch_ctf.py', 'stage_c/analyze_ctf.py', 'stage_c/flag_patch.py', 'stage_c/guard_adapter.py',
          'stage_c/budget.py', 'stage_c/challenge_manifest.json', 'stage_c/development_manifest.json']
PRIVATE = ['image_lock.json', 'flag_patches.json', 'resolved_tasks.json', 'resolved_development_tasks.json']


def text_hash(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def sources():
    names = sorted(p.name for p in HERE.iterdir() if p.suffix in ('.py', '.sh', '.json', '.md')
                   and p.name not in ('v2_freeze.json',) and not p.name.startswith('V2-EXECUTION'))
    return names + ['agent_image/Dockerfile']


def snapshot():
    sys.path.insert(0, str(HERE))
    from environment_v2 import agent_v2_image_id
    return {'study': 'CTF v2',
            'sha256': {n: text_hash(HERE/n) for n in sources()},
            'reused_sha256': {n: text_hash(HERE.parent/n) for n in REUSED},
            'private_sha256': {n: hashlib.sha256((STAGE_C_CACHE/n).read_bytes()).hexdigest() for n in PRIVATE
                               if (STAGE_C_CACHE/n).exists()},
            'agent_v2_image': agent_v2_image_id()}


def verify(value):
    if not value.get('externally_timestamped_before_collection'):
        raise PermissionError('Not a pushed pre-collection freeze')
    current = snapshot()
    for key in ('sha256', 'reused_sha256', 'private_sha256', 'agent_v2_image'):
        if value[key] != current[key]:
            changed = (sorted(k for k in set(value[key]) | set(current[key]) if value[key].get(k) != current[key].get(k))
                       if isinstance(current[key], dict) else [key])
            raise ValueError('Frozen CTF v2 content changed: %s %s' % (key, changed))


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if action == 'write':
        if not json.loads((HERE/'v2_config.json').read_text()).get('allow_live_model_calls'):
            raise SystemExit('Freeze requires the collection configuration')
        value = dict(snapshot(), prepared_at=datetime.now(timezone.utc).isoformat(),
                     status='collection freeze; counts only once its commit is pushed',
                     externally_timestamped_before_collection=True)
        (HERE/'v2_freeze.json').write_text(json.dumps(value, indent=1)+'\n')
        verify(value)
        print('CTF v2 freeze written and verified; commit and push before launch')
    else:
        verify(json.loads((HERE/'v2_freeze.json').read_text()))
        print('CTF v2 freeze verifies')
