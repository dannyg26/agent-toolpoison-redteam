"""Download the pinned run 1 datasets into the private WSL cache and record SHA-256 hashes.

Every source is pinned to a commit or dataset revision. Files are data only: nothing downloaded here is
imported or executed by this script. Output: CACHE/vendor/<name>/... and CACHE/dataset_hashes.json.
"""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

CACHE = Path('/home/capstone-study/stage_d')
GH = 'https://raw.githubusercontent.com/%s/%s/%s'
SOURCES = {
    'cybermetric': ('CyberMetric/CyberMetric', '294662b03be73a9c7c73918f687882c1ba637c47',
                    ['CyberMetric-500-v1.json', 'README.md']),
    'xstest': ('paul-rottger/xstest', 'd7bb5bd738c1fcbc36edd83d5e7d1b71a3e2d84d',
               ['xstest_prompts.csv', 'LICENSE']),
    'cyberseceval': ('meta-llama/PurpleLlama', '0654501399e7cbd560db9501965dc09c567a5563',
                     ['CybersecurityBenchmarks/datasets/mitre_frr/mitre_frr.json',
                      'CybersecurityBenchmarks/datasets/mitre/mitre_benchmark_100_per_category_with_augmentation.json',
                      'CybersecurityBenchmarks/LICENSE']),
    'strongreject': ('alexandrasouly/strongreject', 'f7cad6c17e624e21d8df2278e918ae1dddb4cb56',
                     ['strongreject_dataset/strongreject_dataset.csv', 'LICENSE']),
}
TARBALLS = {   # whole repositories at a pinned commit; extracted, never executed here
    'cweval': ('Co1lin/CWEval', 'e9a2a124c8c53679b6d8d27adfd2f6c40e7576d7'),
    'injecagent': ('uiuc-kang-lab/InjecAgent', 'f19c9f2c79a41046eb13c03c51a24c567a8ffa07'),
}
HF = {
    'wmdp': ('https://huggingface.co/datasets/cais/wmdp/resolve/%s/wmdp-cyber/test-00000-of-00001.parquet',
             '7125571f22f032c56415e7980f48d877dd830ff8', 'wmdp-cyber-test.parquet'),
}


def fetch(url, limit=60_000_000):
    request = urllib.request.Request(url, headers={'User-Agent': 'research-client'})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read(limit+1)
    if len(data) > limit:
        raise ValueError('Download exceeds bound: '+url)
    return data


def main():
    hashes = {}
    def save(name, relative, data):
        target = (CACHE/'vendor'/name/relative).resolve()
        if not target.is_relative_to((CACHE/'vendor'/name).resolve()):
            raise ValueError('Path escapes vendor directory')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        hashes[name+'/'+relative] = hashlib.sha256(data).hexdigest()
    for name, (repo, commit, files) in SOURCES.items():
        for path in files:
            save(name, path, fetch(GH % (repo, commit, path)))
    for name, (repo, commit) in TARBALLS.items():
        data = fetch('https://codeload.github.com/%s/tar.gz/%s' % (repo, commit))
        hashes[name+'/_archive.tar.gz'] = hashlib.sha256(data).hexdigest()
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue                      # no links, devices or directories from the archive
                relative = member.name.split('/', 1)[1] if '/' in member.name else member.name
                save(name, relative, tar.extractfile(member).read())
    for name, (url, revision, filename) in HF.items():
        save(name, filename, fetch(url % revision))
    pins = {'github': {k: {'repo': v[0], 'commit': v[1]} for k, v in {**SOURCES, **TARBALLS}.items()},
            'huggingface': {k: {'url': v[0] % v[1], 'revision': v[1]} for k, v in HF.items()}}
    (CACHE/'dataset_hashes.json').write_text(json.dumps({'pins': pins, 'sha256': hashes}, indent=1)+'\n')
    print(json.dumps({'files': len(hashes), 'pins': pins}, indent=1))


if __name__ == '__main__':
    main()
