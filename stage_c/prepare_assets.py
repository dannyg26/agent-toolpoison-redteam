"""Fetch pinned CTF packages into Linux storage. Never run a solution or model."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
CACHE = Path('/home/capstone-study/stage_c')
HEADERS = {'User-Agent': 'capstone-pinned-asset-preparation'}


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=90) as response:
        data = response.read(12_000_001)
    if len(data) > 12_000_000:
        raise ValueError('Asset exceeds the reviewed download size bound')
    return data


def normal(value):
    return re.sub('[^a-z0-9]', '', value.lower())


def resolve(manifest, index):
    resolved = []
    for task in manifest['tasks']:
        matches = [(key, entry) for key, entry in index.items()
                   if entry['category'] == task['category']
                   and entry['year'] == task['event'][:4]
                   and entry['event'] == ('CSAW-Quals' if task['event'].endswith('q') else 'CSAW-Finals')
                   and normal(entry['challenge']) == normal(task['name'])]
        if len(matches) != 1:
            raise ValueError(f"Cannot uniquely resolve {task['id']}")
        key, entry = matches[0]
        source = PurePosixPath(entry['path'])
        if source.is_absolute() or '..' in source.parts or source.parts[0] != 'ctftiny':
            raise ValueError('Unexpected dataset path')
        resolved.append(dict(task, dataset_key=key, source_path=str(source)))
    return resolved


def main():
    if os.name != 'posix':
        raise SystemExit('Run this program inside Ubuntu WSL, not Windows.')
    config = json.loads((HERE / 'study_config.json').read_text())
    manifest = json.loads((HERE / 'challenge_manifest.json').read_text())
    repo, revision = config['benchmark_repository'], config['benchmark_revision']
    base = f'https://raw.githubusercontent.com/{repo}/{revision}/'
    index_data = fetch(base + 'ctftiny.json')
    resolved = resolve(manifest, json.loads(index_data))
    tree = json.loads(fetch(f'https://api.github.com/repos/{repo}/git/trees/{revision}?recursive=1'))
    if tree.get('truncated'):
        raise ValueError('Incomplete repository tree')
    prefixes = [task['source_path'] + '/' for task in resolved]
    blobs = [entry for entry in tree['tree'] if entry['type'] == 'blob'
             and (entry['path'] in {'LICENSE', 'ctftiny.json'}
                  or any(entry['path'].startswith(prefix) for prefix in prefixes))]
    if sum(entry.get('size', 0) for entry in blobs) > 128_000_000:
        raise ValueError('Selected packages exceed the reviewed download size bound')
    destination = CACHE / 'vendor' / 'CTFTiny'
    destination.mkdir(parents=True, exist_ok=True)
    os.chmod(CACHE.parent, 0o700)

    def download(entry):
        relative = PurePosixPath(entry['path'])
        if relative.is_absolute() or '..' in relative.parts or entry.get('mode') not in {'100644', '100755'}:
            raise ValueError('Unsafe or unsupported asset entry')
        path = destination.joinpath(*relative.parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        def valid(data):
            return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == entry['sha']
        data = path.read_bytes() if path.is_file() else b''
        if not valid(data):
            data = fetch(base + urllib.parse.quote(entry['path'], safe='/'))
            if not valid(data):
                raise ValueError('Downloaded asset does not match the pinned Git blob')
            path.write_bytes(data)
        path.chmod(0o755 if entry['mode'] == '100755' else 0o644)
        return {'path': entry['path'], 'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        hashes = list(pool.map(download, blobs))
    (CACHE / 'resolved_tasks.json').write_text(json.dumps(resolved, indent=2) + '\n')
    (CACHE / 'asset_hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    summary = []
    for task in resolved:
        directory = destination / task['source_path']
        meta = json.loads((directory / 'challenge.json').read_text())
        for filename in meta.get('files', []):
            candidate = (directory / filename).resolve()
            if not candidate.is_relative_to(directory.resolve()) or not candidate.is_file():
                raise ValueError('Invalid intended starter file')
        summary.append({'id': task['id'], 'source_path': task['source_path'],
                        'files': meta.get('files', []), 'port': meta.get('internal_port'),
                        'compose': meta.get('compose'),
                        'compose_files': [str(p.relative_to(directory)) for p in directory.glob('*compose*.y*ml')],
                        'flag_type': type(meta.get('flag')).__name__})
    (HERE / 'asset_inventory.json').write_text(json.dumps({
        'revision': revision, 'tasks': summary, 'files_downloaded': len(hashes),
        'download_bytes': sum(entry['size'] for entry in hashes),
        'storage': 'private Linux cache; no challenge execution or model calls',
        'asset_manifest_sha256': hashlib.sha256((CACHE / 'asset_hashes.json').read_bytes()).hexdigest(),
    }, indent=2) + '\n')
    print(json.dumps({'tasks': len(summary), 'files': len(hashes),
                      'download_mb': round(sum(entry['size'] for entry in hashes)/1e6, 2)}))


if __name__ == '__main__':
    main()
