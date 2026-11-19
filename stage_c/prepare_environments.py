"""Pull official task images, pin digests, build tools. No challenge/model execution."""
import argparse
import hashlib
import json
from pathlib import Path

from environment import AGENT_TAG, CACHE, HERE, command, docker, load_task


def main():
    import yaml
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-agent', action='store_true')
    parser.add_argument('--pull-targets', action='store_true')
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    lockpath = CACHE/'image_lock.json'
    lock = json.loads(lockpath.read_text()) if lockpath.exists() else {'targets': {}}
    if args.build_agent:
        source_hash = hashlib.sha256((HERE/'agent_image/Dockerfile').read_bytes()).hexdigest()
        result = docker('build', '-t', AGENT_TAG, str(HERE/'agent_image'), timeout=900)
        (CACHE/'agent-build.log').write_text(result['output'])
        lock['agent'] = docker('image', 'inspect', AGENT_TAG, '--format', '{{.Id}}')['output'].strip()
        lock['agent_dockerfile_sha256'] = source_hash
        lockpath.write_text(json.dumps(lock, indent=2)+'\n')
        print('Agent tool image built and pinned', flush=True)
    failures = []
    if args.pull_targets:
        images = set()
        tasks = json.loads((HERE/'challenge_manifest.json').read_text())['tasks']
        if (HERE/'development_manifest.json').is_file():
            tasks += json.loads((HERE/'development_manifest.json').read_text())['tasks']
        for task in tasks:
            _, directory, _ = load_task(task['id'])
            doc = yaml.safe_load((directory/'docker-compose.yml').read_text())
            images.update(service['image'] for service in doc['services'].values())
        for image in sorted(images):
            try:
                reference = lock['targets'].get(image, image)
                present = docker('image', 'inspect', reference, check=False)
                if present['exit_code'] != 0:
                    docker('pull', reference, timeout=600)
                digests = json.loads(docker('image', 'inspect', reference, '--format', '{{json .RepoDigests}}')['output'])
                if not digests:
                    raise ValueError('No registry digest recorded')
                lock['targets'][image] = digests[0]
                lockpath.write_text(json.dumps(lock, indent=2)+'\n')
                print('Pinned', image, flush=True)
            except Exception as error:
                failures.append({'image': image, 'error': str(error)})
                print('Image unavailable:', image, flush=True)
    report = {'agent_built': 'agent' in lock, 'target_images_pinned': len(lock['targets']),
              'failures': failures, 'model_calls': 0, 'paid_spend_usd': 0}
    (HERE/'image_preparation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
