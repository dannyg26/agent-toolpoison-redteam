"""Free deployment/grader-integrity checks. No model, exploit or solve attempt."""
import hashlib
import argparse
import json
from pathlib import Path
import time

from environment import CACHE, HERE, Environment, docker
from flag_patch import validate_template


def discover_flags(env):
    expected = env.metadata['flag']
    config = json.loads((env.directory/'compose.json').read_text())
    patches = []
    found_env = False
    for service in config['services']:
        if service == 'agent':
            continue
        container = env.compose('ps', '-a', '-q', service)['output'].strip()
        info = json.loads(docker('inspect', container)['output'])[0]
        found_env |= any(expected in value for value in info['Config'].get('Env', []))
        match = docker('exec', '--user', 'root', container, 'grep', '-rlF', '--', expected,
                       '/home', '/app', '/opt/chal', '/var/www', '/usr/local/nginx/conf',
                       '/etc/nginx', '/etc/apache2', '/flag', '/flag.txt', timeout=30, check=False)
        files = [line for line in match['output'].splitlines() if line.startswith('/')]
        for path in files:
            canonical = docker('exec', '--user', 'root', container, 'readlink', '-f', path)['output'].strip()
            attrs = docker('exec', '--user', 'root', container, 'stat', '-c', '%a %u %g', canonical)['output'].split()
            template = CACHE/'flag_templates'/env.task_id/(service+'-'+hashlib.sha256(canonical.encode()).hexdigest())
            template.parent.mkdir(parents=True, exist_ok=True)
            docker('cp', container+':'+canonical, template)
            data = template.read_bytes()
            transformation = validate_template(data, expected)
            patches.append({'service': service, 'path': canonical, 'template': str(template),
                            'mode': int(attrs[0], 8), 'uid': int(attrs[1]), 'gid': int(attrs[2]),
                            'sha256': hashlib.sha256(data).hexdigest(),
                            'transformation': transformation})
    if not patches and not found_env:
        raise ValueError('Expected official flag was not found in deployed service data or environment')
    return {'files': patches, 'environment': found_env, 'validated': False}


def check_randomized(env, patches):
    # Compare fresh secrets only inside the trusted controller; never publish their values.
    matched = False
    for patch in patches['files']:
        container = env.compose('ps', '-a', '-q', patch['service'])['output'].strip()
        # Binary templates require a binary-safe Docker copy rather than decoded terminal output.
        verified = env.directory/('verified-'+hashlib.sha256(patch['path'].encode()).hexdigest())
        docker('cp', container+':'+patch['path'], verified)
        data = verified.read_bytes()
        if env.expected_flag.encode() not in data or env.metadata['flag'].encode() in data:
            raise ValueError('Fresh-secret file check failed')
        matched = True
    if patches['environment']:
        for service in env.document['services']:
            if service == 'agent':
                continue
            container = env.compose('ps', '-a', '-q', service)['output'].strip()
            info = json.loads(docker('inspect', container)['output'])[0]
            values = info['Config'].get('Env', [])
            if any(env.metadata['flag'] in value for value in values):
                raise ValueError('Original secret remains in service environment')
            matched |= any(env.expected_flag in value for value in values)
    if not matched:
        raise ValueError('No fresh secret deployed')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', help='Repair/recheck one planned environment; never a model run')
    args = parser.parse_args()
    path = CACHE/'flag_patches.json'
    patches = json.loads(path.read_text()) if path.exists() else {}
    report_path = HERE/'challenge_health.json'
    outcomes = json.loads(report_path.read_text())['tasks'] if args.only and report_path.exists() else []
    tasks = json.loads((HERE/'challenge_manifest.json').read_text())['tasks']
    if args.only and args.only not in {task['id'] for task in tasks}:
        raise ValueError('Task is not in the planned inventory')
    for task in tasks:
        if args.only and task['id'] != args.only:
            continue
        start = time.monotonic()
        outcome = {'task_id': task['id'], 'healthy': False, 'fresh_secret_verified': False}
        try:
            with Environment(task['id'], discovery=True) as env:
                env.wait_healthy()
                patch = discover_flags(env)
            # Permit the validation deployment; only mark the public check passed after it succeeds.
            patches[task['id']] = dict(patch, validated=True)
            path.write_text(json.dumps(patches, indent=2)+'\n')
            with Environment(task['id']) as env:
                env.wait_healthy()
                check_randomized(env, patch)
            outcome.update(healthy=True, fresh_secret_verified=True)
            print('Validated', task['id'], flush=True)
        except Exception as error:
            if task['id'] in patches:
                patches[task['id']]['validated'] = False
                path.write_text(json.dumps(patches, indent=2)+'\n')
            outcome['error_type'] = type(error).__name__
            # Full errors can contain service data; retain them only in private Linux storage.
            (CACHE/(task['id']+'-health-error.txt')).write_text(str(error))
            print('Needs repair', task['id'], outcome['error_type'], flush=True)
        outcome['elapsed_seconds'] = round(time.monotonic()-start, 2)
        outcomes = [row for row in outcomes if row['task_id'] != task['id']]
        outcomes.append(outcome)
        (HERE/'challenge_health.json').write_text(json.dumps({
            'scope': 'environment and private checker checks only; no model outcomes',
            'planned': len(tasks), 'checked': len(outcomes), 'tasks': outcomes,
            'paid_spend_usd': 0, 'model_calls': 0}, indent=2)+'\n')
    if len(outcomes) != len(tasks) or not all(row['healthy'] for row in outcomes):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
