"""CTF v2 launcher for ONE arm per pod. Dry run by default; --check-access is read-only; --launch spends.

Reuses the stage C launcher's tested helpers (API, SSH, detached commands, termination) and the stage B
guard. Flow: preflight -> create one pod -> arm guard -> v2_pod.sh (install, download, serve) -> SSH tunnel
to 127.0.0.1:18000 -> run_arm_v2.py development then test phase on this host -> fetch pod logs ->
terminate in `finally`. Keys are read from private files and never printed.
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

CACHE = Path('/home/capstone-study/stage_e')
CONFIG = json.loads((HERE/'v2_config.json').read_text())
POD_KEY, GUARD_OUT, POD_OUT = '/root/guard.key', '/root/out/v2_guard', '/root/out/v2'
ARCHIVE_RESERVE_SECONDS = 5*60


def budget():
    hourly = float(CONFIG['maximum_hourly_usd_including_disk'])
    return hourly, round(hourly*CONFIG['hard_session_minutes']/60 + float(CONFIG['delayed_charge_reserve_usd']), 2)


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
    result = {'existing_pods': len(rows), 'gpu': C.GPU, 'quoted_hourly_with_disk': round(hourly, 4),
              'hourly_ceiling': ceiling, 'balance_usd': round(balance, 4), 'current_spend_per_hour': spend,
              'maximum_additional_spend_usd': cap}
    result['ok'] = not rows and spend == 0 and hourly <= ceiling and balance >= cap
    return result


def package():
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as tar:
        def add(name, data, mode=0o600):
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), mode
            tar.addfile(info, io.BytesIO(data))
        add('stage_e/v2_pod.sh', (HERE/'v2_pod.sh').read_bytes().replace(b'\r\n', b'\n'), 0o700)
        add('stage_e/v2_config.json', (HERE/'v2_config.json').read_bytes())
        add('stage_e/guard_config.json', json.dumps(guard_config()).encode())
        add('stage_b/pod_guard.py', (HERE.parent/'stage_b/pod_guard.py').read_bytes().replace(b'\r\n', b'\n'))
    return stream.getvalue()


def check_frozen_and_pushed():
    from freeze_v2 import verify
    verify(json.loads((HERE/'v2_freeze.json').read_text()))
    git = ['git', '-c', 'safe.directory=*', '-C', str(HERE)]
    if subprocess.run(git+['status', '--porcelain', '--', '.'], capture_output=True, text=True, check=True).stdout.strip():
        raise SystemExit('stage_e has uncommitted changes; commit and push the freeze first')
    head = subprocess.run(git+['rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    if not subprocess.run(git+['branch', '-r', '--contains', head], capture_output=True, text=True, check=True).stdout.strip():
        raise SystemExit('The frozen commit is not on any remote branch; push it before launch')
    return head


def pod_log(pod):
    return pod.run('cat %s/progress.log 2>/dev/null' % POD_OUT, check=False, timeout=60).stdout.decode()


def launch(key, arm, hourly, session_id, out):
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'ctf-v2', '-f', str(out/'ephemeral_ssh_key')],
                   check=True)
    name = 'ctf-v2-%s-%s' % (arm, uuid.uuid4().hex[:6])
    payload = {'name': name, 'image': C.IMAGE, 'cloud': 'SECURE', 'disk': C.DISK_GB, 'startSsh': True,
               'gpu': {'id': C.GPU, 'count': 1, 'minCudaVersion': '12.8'}, 'ports': ['22/tcp'],
               'env': {'PUBLIC_KEY': (out/'ephemeral_ssh_key.pub').read_text().strip()}}
    print('creating ONE %s pod for arm %s at quote $%.3f/h; hard stop %d min after creation'
          % (C.GPU, arm, hourly, CONFIG['hard_session_minutes']), flush=True)
    requested = time.time()
    try:
        pod = C.api('POST', '/pods', key, payload)
    except urllib.error.HTTPError as error:
        try:
            detail = error.read(4000).decode(errors='replace')
        except OSError:
            detail = 'no detail'
        detail = detail.replace(key, '[REDACTED]')[:500]
        (out/'allocation_error.json').write_text(json.dumps({'status': error.code, 'detail': detail})+'\n')
        raise SystemExit('RunPod refused allocation: HTTP %d: %s; no retry' % (error.code, detail)) from None
    pod_id = pod['id']
    from guard_adapter import guard
    created = guard.parse_created(pod) if pod.get('createdAt') else requested
    hard_stop = created + CONFIG['hard_session_minutes']*60
    soft_stop = hard_stop - ARCHIVE_RESERVE_SECONDS
    status = {'pod_id': pod_id, 'arm': arm, 'quote_hourly': hourly, 'session': session_id, 'steps': []}
    stopped = threading.Event()
    def watchdog():
        if not stopped.wait(max(0, hard_stop-30-time.time())):
            print('local hard-stop watchdog terminating pod', flush=True)
            C.terminate(pod_id, key)
    threading.Thread(target=watchdog, daemon=True).start()
    client = tunnel = None
    try:
        client = C.wait_for_ssh(pod_id, key, out, soft_stop)
        client.run('mkdir -p /root/out && tar -xzf - -C /root', stdin=package(), timeout=300)
        client.run('umask 077 && cat > %s' % POD_KEY, stdin=(key+'\n').encode())
        client.run(C.background('env RUNPOD_POD_ID=%s python3 /root/stage_b/pod_guard.py --arm --config '
                                '/root/stage_e/guard_config.json --key-file %s --out %s'
                                % (shlex.quote(pod_id), POD_KEY, GUARD_OUT), '/root/out/guard.log'))
        if not C.wait_until(lambda: client.run('test -s %s/guard_ready.json' % GUARD_OUT, check=False).returncode == 0, 120, 5):
            raise RuntimeError('Pod-side guard did not arm; nothing else started')
        status['guard'] = json.loads(client.run('cat %s/guard_ready.json' % GUARD_OUT).stdout)
        client.run(C.background('bash /root/stage_e/v2_pod.sh %s' % shlex.quote(arm), '/root/out/v2_pod.log',
                                '/root/stage_e'))
        print('guard armed; v2_pod.sh started', flush=True)
        seen = 0
        while True:
            lines = pod_log(client).splitlines()
            for line in lines[seen:]:
                print('pod:', line, flush=True)
            seen = len(lines)
            if any(l.split(' ', 1)[-1].startswith('SERVING') for l in lines):
                break
            if any('FAILED' in l or 'DRIVER_EXIT' in l for l in lines) or time.time() > soft_stop:
                raise RuntimeError('Model server did not come up')
            time.sleep(20)
        tunnel = client.tunnel()
        time.sleep(3)
        if tunnel.poll() is not None:
            raise RuntimeError('SSH tunnel to the model server failed')
        for phase in ('development', 'test'):
            argv = [sys.executable, 'run_arm_v2.py', '--arm', arm, '--phase', phase, '--endpoint',
                    'http://127.0.0.1:%d/v1' % C.LOCAL_PORT, '--session', session_id,
                    '--soft-stop-epoch', '%.0f' % soft_stop, '--run-approved']
            print('running', phase, flush=True)
            code = subprocess.run(argv, cwd=HERE).returncode
            status['steps'].append({'phase': phase, 'exit_code': code})
            if code:
                print('phase failed; stopping this session', flush=True)
                break
    finally:
        stopped.set()
        if tunnel:
            tunnel.terminate()
        if client:
            for name in ('progress.log', 'vllm.log', 'install.log', 'pip-freeze.txt', 'download.log'):
                data = client.run('tail -c 3000000 %s/%s 2>/dev/null' % (POD_OUT, name), check=False, timeout=120).stdout
                (out/'pod_logs').mkdir(exist_ok=True)
                (out/'pod_logs'/name).write_bytes(data)
        status['terminated'] = C.terminate(pod_id, key)
        status['elapsed_minutes_from_creation'] = round((time.time()-created)/60, 2)
        status['maximum_quoted_spend_before_tax'] = round((time.time()-created)/3600*hourly, 3)
        (out/'run_status.json').write_text(json.dumps(status, indent=2)+'\n')
        print(json.dumps({k: status.get(k) for k in ('pod_id', 'arm', 'terminated', 'elapsed_minutes_from_creation',
                                                     'maximum_quoted_spend_before_tax')}), flush=True)
        if not status['terminated']:
            raise RuntimeError('Termination not confirmed; check the RunPod console now. Guard is the backup.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check-access', action='store_true')
    mode.add_argument('--launch', action='store_true')
    parser.add_argument('--arm', choices=sorted(CONFIG['arms']))
    parser.add_argument('--key-file')
    parser.add_argument('--balance-key-file')
    parser.add_argument('--session')
    parser.add_argument('--approved-max-usd', type=float)
    args = parser.parse_args()
    _, cap = budget()
    if not (args.check_access or args.launch):
        print(json.dumps({'dry_run': True, 'api_calls': 0, 'cap_usd_per_arm': cap, 'arm_order': CONFIG['arm_order'],
                          'package_bytes': len(package())}, indent=2))
        return
    key = Path(args.key_file).read_text().strip()
    balance_key = Path(args.balance_key_file).read_text().strip()
    check = preflight(key, balance_key)
    print(json.dumps(check, indent=2), flush=True)
    if args.check_access:
        print('read-only access check complete; no pod created')
        return
    if not check['ok']:
        raise SystemExit('Preflight failed: existing pods, active spend, quote above ceiling or low balance')
    if not args.arm or args.approved_max_usd is None or args.approved_max_usd < cap:
        raise SystemExit('Pass --arm and --approved-max-usd with the ceiling approved in chat')
    if not CONFIG.get('allow_live_model_calls'):
        raise SystemExit('Live model calls are disabled in v2_config.json')
    commit = check_frozen_and_pushed()
    if not args.session or not args.session.isalnum():
        parser.error('--session must be a new alphanumeric identifier')
    out = CACHE/'launch'/args.session
    if out.exists() or (CACHE/'private'/args.session).exists() and any((CACHE/'private'/args.session).iterdir()):
        parser.error('Session already exists; a paid launch is never silently repeated')
    out.mkdir(parents=True, mode=0o700)
    (out/'launch.json').write_text(json.dumps({'frozen_commit': commit, 'arm': args.arm, 'preflight': check,
        'approved_max_usd': args.approved_max_usd,
        'config_sha256': hashlib.sha256((HERE/'v2_config.json').read_bytes()).hexdigest()}, indent=2)+'\n')
    launch(key, args.arm, check['quoted_hourly_with_disk'], args.session, out)


if __name__ == '__main__':
    main()
