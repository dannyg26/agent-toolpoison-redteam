"""Pin three disjoint NYU development cases using metadata only, then fetch assets."""
import concurrent.futures
import hashlib
import json
from pathlib import PurePosixPath

from prepare_assets import CACHE, HERE, fetch


def main():
    config = json.loads((HERE/'study_config.json').read_text())
    repo, revision = config['parent_repository'], config['parent_revision']
    base = f'https://raw.githubusercontent.com/{repo}/{revision}/'
    raw = fetch(base+'development_dataset.json')
    index = json.loads(raw)
    tree = json.loads(fetch(f'https://api.github.com/repos/{repo}/git/trees/{revision}?recursive=1'))
    if tree.get('truncated'):
        raise ValueError('Development source tree is incomplete')
    paths = {entry['path'] for entry in tree['tree']}
    selected = []
    for category, count in [('pwn', 2), ('web', 1)]:
        candidates = [(key, entry) for key, entry in index.items() if entry['category'] == category
                      and entry['path']+'/docker-compose.yml' in paths]
        candidates.sort(key=lambda item: hashlib.sha256(('stage_c.dev.v1:'+item[0]).encode()).hexdigest())
        for key, entry in candidates[:count]:
            selected.append({'id': key, 'category': category, 'source_path': entry['path'],
                             'vendor_folder': 'NYU_CTF_Bench'})
    if len(selected) != 3:
        raise ValueError('Insufficient eligible development environments')
    test_ids = {task['id'] for task in json.loads((HERE/'challenge_manifest.json').read_text())['tasks']}
    if any(task['id'] in test_ids for task in selected):
        raise ValueError('Development/test task overlap')
    prefixes = [task['source_path']+'/' for task in selected]
    blobs = [entry for entry in tree['tree'] if entry['type'] == 'blob'
             and (entry['path'] == 'LICENSE' or any(entry['path'].startswith(p) for p in prefixes))]
    if sum(entry.get('size', 0) for entry in blobs) > 128_000_000:
        raise ValueError('Development download exceeds the preparation bound')
    destination = CACHE/'vendor/NYU_CTF_Bench'
    destination.mkdir(parents=True, exist_ok=True)
    def download(entry):
        import urllib.parse
        path = PurePosixPath(entry['path'])
        if path.is_absolute() or '..' in path.parts or entry['mode'] not in ('100644', '100755'):
            raise ValueError('Unsafe development asset path')
        data = fetch(base+urllib.parse.quote(str(path), safe='/'))
        if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() != entry['sha']:
            raise ValueError('Development asset hash mismatch')
        target = destination.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o755 if entry['mode'] == '100755' else 0o644)
        return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest()}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        hashes = list(pool.map(download, blobs))
    (CACHE/'resolved_development_tasks.json').write_text(json.dumps(selected, indent=2)+'\n')
    (CACHE/'development_asset_hashes.json').write_text(json.dumps(hashes, indent=2)+'\n')
    (HERE/'development_manifest.json').write_text(json.dumps({
        'scope': 'compatibility/timing only; never pooled with the 14 test tasks',
        'source_revision': revision, 'index_sha256': hashlib.sha256(raw).hexdigest(),
        'source_index_entries': len(index),
        'selection': 'Hash-ranked first two pwn and first web entries with a Compose file; no outcomes used',
        'tasks': selected,
    }, indent=2)+'\n')
    config['development_task_ids'] = [task['id'] for task in selected]
    (HERE/'study_config.json').write_text(json.dumps(config, indent=2)+'\n')
    print(json.dumps({'selected_development_ids': config['development_task_ids'], 'files': len(hashes)}))


if __name__ == '__main__':
    main()
