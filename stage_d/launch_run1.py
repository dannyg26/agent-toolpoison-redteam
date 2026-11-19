"""Stage D run 1 launcher. Dry run by default; --check-access is read-only; --launch spends.

Reuses the stage C launcher's tested helpers (API, preflight pieces, SSH, detached commands, termination).
Rents ONE A100 pod, arms the unmodified stage B pod guard first, uploads the frozen items and pod
scripts, starts run1_pod.sh detached, polls progress, downloads results, and terminates in `finally`.
Keys are read from private files and never printed. No payment, retry rental or second pod.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import threading
import time
import urllib.error
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'stage_c'))
import launch_ctf as C  # noqa: E402

CACHE = Path('/home/capstone-study/stage_d')
CONFIG = json.loads((HERE/'run1_config.json').read_text())
POD_ROOT, POD_OUT, POD_KEY = '/root/stage_d', '/root/out/stage_d', '/root/guard.key'
GUARD_OUT = '/root/out/stage_d_guard'
POD_SOURCES = ['pod_generate.py', 'pod_judge.py', 'injecagent_port.py', 'build_items.py', 'run1_config.json',
               'run1_pod.sh']
ROOT_SOURCES = ['sr_judge.py', 'judge_templates.json']
ARCHIVE_RESERVE_SECONDS = 8*60


def budget():
    hourly = float(CONFIG['maximum_hourly_usd_including_disk'])
    cap = hourly*CONFIG['hard_session_minutes']/60 + float(CONFIG['delayed_charge_reserve_usd'])
    return hourly, round(cap, 2)


def guard_config():
    hourly, _ = budget()
    return {'hourly_usd_including_disk': hourly, 'maximum_compute_usd': hourly*CONFIG['hard_session_minutes']/60,
            'maximum_session_minutes': CONFIG['hard_session_minutes']}


def preflight(key, balance_key):
    rows = C.api('GET', '/pods', key)
    rows = rows if isinstance(rows, list) else rows.get('pods', [])
    gpu = next(x for x in C.api('GET', '/catalog/gpus', key)['gpus'] if x['id'] == C.GPU)
    hourly = C.quoted_hourly(float(gpu['price']['secure']))
    balance, spend = C.read_balance(balance_key)
    ceiling, cap = budget()
    result = {'existing_pods': len(rows), 'gpu': C.GPU, 'secure_gpu_price': gpu['price']['secure'],
              'quoted_hourly_with_disk': round(hourly, 4), 'hourly_ceiling': ceiling, 'balance_usd': round(balance, 4),
              'current_spend_per_hour': spend, 'maximum_additional_spend_usd': cap,
              'cost_at_quote_for_full_session_usd': round(hourly*CONFIG['hard_session_minutes']/60, 4)}
    result['ok'] = not rows and spend == 0 and hourly <= ceiling and balance >= cap
    return result


def injec_files():
    from build_items import injecagent_prompts, tool_dict
    system, user = injecagent_prompts()
    simulated = (CACHE/'vendor/injecagent/data/attacker_simulated_responses.json').read_bytes()
    return {'prompts.json': json.dumps({'system': system, 'user': user}).encode(),
            'tools.json': json.dumps(tool_dict()).encode(), 'simulated.json': simulated}


def package():
    stream = io.BytesIO()
    def add(tar, name, data):
        info = tarfile.TarInfo(name)
        info.size, info.mode = len(data), 0o700 if name.endswith('.sh') else 0o600
        tar.addfile(info, io.BytesIO(data))
    with tarfile.open(fileobj=stream, mode='w:gz') as tar:
        for name in POD_SOURCES:
            add(tar, 'stage_d/'+name, (HERE/name).read_bytes().replace(b'\r\n', b'\n'))
        for name in ROOT_SOURCES:
            add(tar, 'stage_d/'+name, (HERE.parent/name).read_bytes().replace(b'\r\n', b'\n'))
        for path in sorted((CACHE/'items').glob('*.jsonl')):
            add(tar, 'stage_d/items/'+path.name, path.read_bytes())
        for name, data in injec_files().items():
            add(tar, 'stage_d/injec/'+name, data)
        add(tar, 'stage_b/pod_guard.py', (HERE.parent/'stage_b/pod_guard.py').read_bytes().replace(b'\r\n', b'\n'))
        add(tar, 'stage_d/guard_config.json', json.dumps(guard_config()).encode())
    return stream.getvalue()


def check_frozen_and_pushed():
    from freeze_run1 import verify
    verify(json.loads((HERE/'run1_freeze.json').read_text()))
    git = ['git', '-c', 'safe.directory=*', '-C', str(HERE)]
    if subprocess.run(git+['status', '--porcelain', '--', '.'], capture_output=True, text=True, check=True).stdout.strip():
        raise SystemExit('stage_d has uncommitted changes; commit and push the freeze first')
    head = subprocess.run(git+['rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    if not subprocess.run(git+['branch', '-r', '--contains', head], capture_output=True, text=True, check=True).stdout.strip():
        raise SystemExit('The frozen commit is not on any remote branch; push it before launch')
    return head


def setup(pod, key, pod_id):
    pod.run('mkdir -p /root/out && tar -xzf - -C /root', stdin=package(), timeout=300)
    pod.run('umask 077 && cat > %s' % POD_KEY, stdin=(key+'\n').encode())
    pod.run(C.background('env RUNPOD_POD_ID=%s python3 /root/stage_b/pod_guard.py --arm --config %s/guard_config.json '
                         '--key-file %s --out %s' % (shlex.quote(pod_id), POD_ROOT, POD_KEY, GUARD_OUT),
                         '/root/out/guard.log'))
    if not C.wait_until(lambda: pod.run('test -s %s/guard_ready.json' % GUARD_OUT, check=False).returncode == 0, 120, 5):
        raise RuntimeError('Pod-side guard did not arm; nothing else started')
    ready = json.loads(pod.run('cat %s/guard_ready.json' % GUARD_OUT).stdout)
    pod.run(C.background('bash %s/run1_pod.sh' % POD_ROOT, '/root/out/run1_pod.log', POD_ROOT))
    return ready


def fetch_results(pod, session):
    result = pod.run('cd /root/out && tar -czf - stage_d', check=False, timeout=600)
    if result.returncode == 0 and result.stdout:
        with tarfile.open(fileobj=io.BytesIO(result.stdout), mode='r:gz') as tar:
            for member in tar.getmembers():
                if member.isfile() and not member.name.startswith('/') and '..' not in member.name:
                    target = session/member.name[len('stage_d/'):] if member.name.startswith('stage_d/') else None
                    if target:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(tar.extractfile(member).read())
        return True
    return False


def launch(key, hourly, session_id, out):
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'stage-d-run1', '-f', str(out/'ephemeral_ssh_key')],
                   check=True)
    name = 'stage-d-run1-'+uuid.uuid4().hex[:8]
    payload = {'name': name, 'image': C.IMAGE, 'cloud': 'SECURE', 'disk': C.DISK_GB, 'startSsh': True,
               'gpu': {'id': C.GPU, 'count': 1, 'minCudaVersion': '12.8'}, 'ports': ['22/tcp'],
               'env': {'PUBLIC_KEY': (out/'ephemeral_ssh_key.pub').read_text().strip()}}
    print('creating ONE %s pod at quote $%.3f/h; hard stop %d minutes after creation'
          % (C.GPU, hourly, CONFIG['hard_session_minutes']), flush=True)
    requested = time.time()
    try:
        pod = C.api('POST', '/pods', key, payload)
    except urllib.error.HTTPError as error:
        raise SystemExit('RunPod refused allocation: HTTP %d; no retry' % error.code) from None
    pod_id = pod['id']
    from guard_adapter import guard
    created = guard.parse_created(pod) if pod.get('createdAt') else requested
    hard_stop = created + CONFIG['hard_session_minutes']*60
    soft_stop = hard_stop - ARCHIVE_RESERVE_SECONDS
    status = {'pod_id': pod_id, 'name': name, 'quote_hourly': hourly, 'session': session_id, 'progress': []}
    stopped = threading.Event()
    def watchdog():
        if not stopped.wait(max(0, hard_stop-30-time.time())):
            print('local hard-stop watchdog terminating pod', flush=True)
            C.terminate(pod_id, key)
    threading.Thread(target=watchdog, daemon=True).start()
    session = CACHE/'sessions'/session_id
    client = None
    try:
        client = C.wait_for_ssh(pod_id, key, out, soft_stop)
        status['guard'] = setup(client, key, pod_id)
        print('guard armed; run1_pod.sh started', flush=True)
        seen = 0
        while time.time() < soft_stop:
            text = client.run('cat %s/progress.log 2>/dev/null' % POD_OUT, check=False, timeout=60).stdout.decode()
            lines = text.splitlines()
            for line in lines[seen:]:
                print('pod:', line, flush=True)
                status['progress'].append(line)
            seen = len(lines)
            if any(line.endswith('ALL_DONE') for line in lines) or any('install FAILED' in l for l in lines):
                break
            time.sleep(30)
        status['results_downloaded'] = fetch_results(client, session)
    finally:
        stopped.set()
        status['terminated'] = C.terminate(pod_id, key)
        status['elapsed_minutes_from_creation'] = round((time.time()-created)/60, 2)
        status['maximum_quoted_spend_before_tax'] = round((time.time()-created)/3600*hourly, 3)
        (out/'run_status.json').write_text(json.dumps(status, indent=2)+'\n')
        print(json.dumps({k: status.get(k) for k in ('pod_id', 'terminated', 'results_downloaded',
                          'elapsed_minutes_from_creation', 'maximum_quoted_spend_before_tax')}), flush=True)
        if not status['terminated']:
            raise RuntimeError('Termination not confirmed; check the RunPod console now. Guard is the backup.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check-access', action='store_true')
    mode.add_argument('--launch', action='store_true')
    parser.add_argument('--key-file')
    parser.add_argument('--balance-key-file')
    parser.add_argument('--session')
    parser.add_argument('--approved-max-usd', type=float)
    args = parser.parse_args()
    hourly_cap, cap = budget()
    if not (args.check_access or args.launch):
        print(json.dumps({'dry_run': True, 'api_calls': 0, 'cap_usd': cap, 'arms': CONFIG['arm_order'],
                          'package_bytes': len(package())}, indent=2))
        return
    if not (args.key_file and args.balance_key_file):
        parser.error('--key-file and --balance-key-file are required')
    key = Path(args.key_file).read_text().strip()
    balance_key = Path(args.balance_key_file).read_text().strip()
    check = preflight(key, balance_key)
    print(json.dumps(check, indent=2), flush=True)
    if args.check_access:
        print('read-only access check complete; no pod created')
        return
    if not check['ok']:
        raise SystemExit('Preflight failed: existing pods, active spend, quote above ceiling or low balance')
    if args.approved_max_usd is None or args.approved_max_usd < cap:
        raise SystemExit('Pass --approved-max-usd with the ceiling approved in chat')
    if not CONFIG.get('allow_live_model_calls'):
        raise SystemExit('Live model calls are disabled in run1_config.json')
    commit = check_frozen_and_pushed()
    if not args.session or not args.session.isalnum() or len(args.session) > 40:
        parser.error('--session must be a new alphanumeric identifier')
    out = CACHE/'launch'/args.session
    if out.exists() or (CACHE/'sessions'/args.session).exists():
        parser.error('Session already exists; a paid launch is never silently repeated')
    out.mkdir(parents=True, mode=0o700)
    (out/'launch.json').write_text(json.dumps({'frozen_commit': commit, 'preflight': check,
        'approved_max_usd': args.approved_max_usd,
        'config_sha256': hashlib.sha256((HERE/'run1_config.json').read_bytes()).hexdigest()}, indent=2)+'\n')
    launch(key, check['quoted_hourly_with_disk'], args.session, out)
    print('run 1 finished; score with: python3 score_run1.py', CACHE/'sessions'/args.session, flush=True)


if __name__ == '__main__':
    main()
