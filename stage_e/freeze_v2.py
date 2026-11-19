"""Write or verify the CTF v2 freeze. Valid only once its commit is pushed (launch_v2.py checks).

Covers stage_e sources/config/protocol, the reused stage B/C files, the stage C private cache artefacts the
v2 sandbox depends on (image lock, vendor asset hashes for the test and development tasks, flag patches,
resolved tasks; every one is mandatory), a re-hash of every pinned vendor file and private checker template
(as stage_c/freeze_tools.private_hashes does), the v2 agent image ID bound to the frozen Dockerfile through
the image label written by build_agent_v2.py, and the passing environment check
(v2_environment_check.json: all_ok, all 14 test + 3 development tasks, run on the frozen image).
Usage: python3 freeze_v2.py write | check
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
STAGE_C_CACHE = Path('/home/capstone-study/stage_c')
STAGE_E_CACHE = Path('/home/capstone-study/stage_e')
REUSED = ['stage_b/pod_guard.py', 'stage_c/environment.py', 'stage_c/endpoint_client.py', 'stage_c/trajectory.py',
          'stage_c/launch_ctf.py', 'stage_c/analyze_ctf.py', 'stage_c/flag_patch.py', 'stage_c/guard_adapter.py',
          'stage_c/budget.py', 'stage_c/challenge_manifest.json', 'stage_c/development_manifest.json']
PRIVATE = ['image_lock.json', 'asset_hashes.json', 'development_asset_hashes.json', 'flag_patches.json',
           'resolved_tasks.json', 'resolved_development_tasks.json']
VENDOR_HASH_FILES = [('asset_hashes.json', 'CTFTiny'), ('development_asset_hashes.json', 'NYU_CTF_Bench')]
ENVIRONMENT_CHECK = STAGE_E_CACHE/'v2_environment_check.json'


def text_hash(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def sources():
    names = sorted(p.name for p in HERE.iterdir() if p.suffix in ('.py', '.sh', '.json', '.md')
                   and p.name not in ('v2_freeze.json',) and not p.name.startswith('V2-EXECUTION'))
    return names + ['agent_image/Dockerfile']


def private_hashes(cache=STAGE_C_CACHE):
    """Hash every mandatory private file and re-verify the vendor files and checker templates they pin."""
    missing = [n for n in PRIVATE if not (cache/n).is_file()]
    if missing:
        raise ValueError('Mandatory private freeze inputs missing: %s' % missing)
    result = {n: hashlib.sha256((cache/n).read_bytes()).hexdigest() for n in PRIVATE}
    for name, folder in VENDOR_HASH_FILES:
        base = (cache/'vendor'/folder).resolve()
        for entry in json.loads((cache/name).read_text()):
            path = (base/entry['path']).resolve()
            if not path.is_relative_to(base) or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
                raise ValueError('Pinned benchmark file changed: %s' % entry['path'])
    patches = json.loads((cache/'flag_patches.json').read_text())
    for task in json.loads((HERE.parent/'stage_c/challenge_manifest.json').read_text())['tasks']:
        if not patches[task['id']]['validated']:
            raise ValueError('Unvalidated test secret deployment')
        for entry in patches[task['id']]['files']:
            path = Path(entry['template']).resolve()
            if (not path.is_relative_to((cache/'flag_templates').resolve()) or
                    hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']):
                raise ValueError('Private checker template changed')
    return result


def planned_task_ids():
    return sorted(t['id'] for name in ('challenge_manifest.json', 'development_manifest.json')
                  for t in json.loads((HERE.parent/'stage_c'/name).read_text())['tasks'])


def environment_check(image, path=ENVIRONMENT_CHECK):
    """The environment check must pass for every planned task on the image being frozen."""
    if not path.is_file():
        raise ValueError('Run check_v2_environment.py before freezing')
    report = json.loads(path.read_text())
    if not report.get('all_ok'):
        raise ValueError('Environment check did not pass')
    if report.get('agent_v2_image') != image:
        raise ValueError('Environment check ran on a different agent image')
    if sorted(report.get('tasks', {})) != planned_task_ids():
        raise ValueError('Environment check does not cover exactly the 14 test + 3 development tasks')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def agent_image_binding():
    sys.path.insert(0, str(HERE))
    from environment_v2 import agent_v2_dockerfile_label, agent_v2_image_id
    image, label = agent_v2_image_id(), agent_v2_dockerfile_label()
    if label != text_hash(HERE/'agent_image/Dockerfile'):
        raise ValueError('Agent v2 image was not built from the current Dockerfile (rebuild with build_agent_v2.py)')
    return image, label


def snapshot():
    image, label = agent_image_binding()
    return {'study': 'CTF v2',
            'sha256': {n: text_hash(HERE/n) for n in sources()},
            'reused_sha256': {n: text_hash(HERE.parent/n) for n in REUSED},
            'private_sha256': private_hashes(),
            'agent_v2_image': image,
            'agent_v2_dockerfile_sha256': label,
            'environment_check_sha256': environment_check(image)}


KEYS = ('sha256', 'reused_sha256', 'private_sha256', 'agent_v2_image', 'agent_v2_dockerfile_sha256',
        'environment_check_sha256')


def verify(value):
    if not value.get('externally_timestamped_before_collection'):
        raise PermissionError('Not a pushed pre-collection freeze')
    current = snapshot()
    for key in KEYS:
        if key not in value:
            raise ValueError('Freeze lacks %s' % key)
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
    elif action == 'dry-run':
        # Computes every freeze input and check without writing anything (no freeze file, no config change).
        value = snapshot()
        print(json.dumps({k: (len(v) if isinstance(v, dict) else v) for k, v in value.items()}, indent=1))
        print('CTF v2 freeze inputs verify (dry run; nothing written)')
    else:
        verify(json.loads((HERE/'v2_freeze.json').read_text()))
        print('CTF v2 freeze verifies')
