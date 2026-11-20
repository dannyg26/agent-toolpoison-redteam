"""Build the F1 item list (all 313 StrongREJECT prompts) from the stage D pinned copy, verifying its hash.
Output: /home/capstone-study/stage_f/items_f1.jsonl and items_f1_manifest.json (count + SHA-256)."""
import csv
import hashlib
import json
from pathlib import Path

STAGE_D = Path('/home/capstone-study/stage_d')
OUT = Path('/home/capstone-study/stage_f')
SOURCE = 'strongreject/strongreject_dataset/strongreject_dataset.csv'


def seed(item_id):
    return int(hashlib.sha256(item_id.encode()).hexdigest()[:8], 16)


def main():
    pinned = json.loads((STAGE_D/'dataset_hashes.json').read_text())['sha256'][SOURCE]
    data = (STAGE_D/'vendor'/SOURCE).read_bytes()
    if hashlib.sha256(data).hexdigest() != pinned:
        raise ValueError('StrongREJECT file does not match its pinned hash')
    rows = list(csv.DictReader(data.decode('utf-8').splitlines()))
    items = [{'id': 'sr-%03d' % i, 'category': r['category'], 'prompt': r['forbidden_prompt'],
              'seed': seed('sr-%03d' % i)} for i, r in enumerate(rows)]
    if len(items) != 313 or len({i['id'] for i in items}) != 313:
        raise ValueError('Unexpected StrongREJECT item count')
    OUT.mkdir(parents=True, exist_ok=True)
    blob = ''.join(json.dumps(i, sort_keys=True)+'\n' for i in items).encode()
    (OUT/'items_f1.jsonl').write_bytes(blob)
    manifest = {'items': len(items), 'sha256': hashlib.sha256(blob).hexdigest(), 'source_sha256': pinned}
    (OUT/'items_f1_manifest.json').write_text(json.dumps(manifest, indent=1)+'\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
