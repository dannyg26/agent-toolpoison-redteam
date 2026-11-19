"""Prepare/check a local snapshot. Drafts are not external pre-registrations."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from environment import CACHE, HERE


def source_hash(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def source_files():
    return sorted([p.name for p in HERE.glob('*.py')] + [
        'study_config.json', 'challenge_manifest.json', 'development_manifest.json',
        'agent_image/Dockerfile', 'REVISED-CAPSTONE-PLAN.md', 'CTF-PROTOCOL.md'])


def private_hashes():
    names = ['image_lock.json', 'asset_hashes.json', 'development_asset_hashes.json', 'flag_patches.json']
    result = {name: hashlib.sha256((CACHE/name).read_bytes()).hexdigest() for name in names}
    lock = json.loads((CACHE/'image_lock.json').read_text())
    if lock.get('agent_dockerfile_sha256') != hashlib.sha256((HERE/'agent_image/Dockerfile').read_bytes()).hexdigest():
        raise ValueError('Agent image was not built from the current Dockerfile')
    for name, folder in [('asset_hashes.json', 'CTFTiny'), ('development_asset_hashes.json', 'NYU_CTF_Bench')]:
        base = (CACHE/'vendor'/folder).resolve()
        for entry in json.loads((CACHE/name).read_text()):
            path = (base/entry['path']).resolve()
            if not path.is_relative_to(base) or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
                raise ValueError('Pinned benchmark file changed')
    patches = json.loads((CACHE/'flag_patches.json').read_text())
    for task in json.loads((HERE/'challenge_manifest.json').read_text())['tasks']:
        if not patches[task['id']]['validated']:
            raise ValueError('Unvalidated test secret deployment')
        for entry in patches[task['id']]['files']:
            path = Path(entry['template']).resolve()
            if (not path.is_relative_to((CACHE/'flag_templates').resolve()) or
                    hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']):
                raise ValueError('Private checker template changed')
    return result


def snapshot():
    return {'prepared_at': datetime.now(timezone.utc).isoformat(),
            'status': 'local draft only; no external timestamp and no collection authorisation',
            'externally_timestamped_before_collection': False,
            'sha256': {name: source_hash(HERE/name) for name in source_files()},
            'external_guard_sha256': source_hash(HERE.parent/'stage_b/pod_guard.py'),
            'private_cache_sha256': private_hashes(),
            'image_lock_sha256': hashlib.sha256((CACHE/'image_lock.json').read_bytes()).hexdigest()}


def verify(value, require_external=True):
    if require_external and not value.get('externally_timestamped_before_collection'):
        raise PermissionError('This is not an externally timestamped pre-collection freeze')
    if set(value['sha256']) != set(source_files()):
        raise ValueError('Freeze omits source files or refers to a different source inventory')
    for name, expected in value['sha256'].items():
        if source_hash(HERE/name) != expected:
            raise ValueError('Frozen source mismatch: '+name)
    if source_hash(HERE.parent/'stage_b/pod_guard.py') != value['external_guard_sha256']:
        raise ValueError('Reused pod guard changed')
    if private_hashes() != value['private_cache_sha256']:
        raise ValueError('Benchmark/image/checker cache changed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['draft', 'check-draft', 'final'])
    args = parser.parse_args()
    path = HERE/'ctf_freeze_draft.json'
    if args.action == 'final':
        # Valid only after the commit that contains it is pushed; launch_ctf.py checks that.
        config = json.loads((HERE/'study_config.json').read_text())
        if not config.get('allow_live_model_calls'):
            raise SystemExit('Final freeze requires the collection configuration')
        value = snapshot()
        value.update(status='collection freeze; counts only once its commit is pushed to the remote',
                     externally_timestamped_before_collection=True)
        verify(value)
        (HERE/'ctf_freeze.json').write_text(json.dumps(value, indent=2)+'\n')
        print('Final freeze written; commit and push it before launch.')
        raise SystemExit(0)
    if args.action == 'draft':
        value = snapshot()
        path.write_text(json.dumps(value, indent=2)+'\n')
    else:
        value = json.loads(path.read_text())
        verify(value, require_external=False)
    print('Local draft snapshot checked; live collection remains disabled.')
