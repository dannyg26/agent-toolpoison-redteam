"""F2 launcher: ONE arm per pod. Dry run by default; --check-access is read-only; --launch spends.

Reuses the frozen CTF v2 launcher (stage_e/launch_v2.py) for preflight, packaging, the stage B guard, the
v2 pod driver (install, download, serve), the SSH tunnel, best-effort log fetching and guaranteed
termination. Differences: hard stop f2.hard_session_minutes (120), the stage F freeze check, sessions under
/home/capstone-study/stage_f, and the run phase calls run_arm_f2.py once (no development phase: v2 already
validated serving and tools for all three arms; a serving health request runs first).
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'stage_e'))
sys.path.insert(0, str(HERE.parent/'stage_c'))
import launch_v2 as L  # noqa: E402

F = json.loads((HERE/'f_config.json').read_text())
L.CONFIG = dict(L.CONFIG, hard_session_minutes=F['f2']['hard_session_minutes'])   # budget/guard use this
C = L.C
CACHE = Path('/home/capstone-study/stage_f')


def check_frozen_and_pushed():
    from freeze_f import check_frozen_and_pushed as check
    return check()


def health(endpoint, arm, timeout=30):
    with urllib.request.urlopen(endpoint+'/models', timeout=timeout) as response:
        return ('csc-'+arm) in response.read().decode(errors='replace')


def launch(key, arm, hourly, session_id, out):
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'stage-f2', '-f', str(out/'ephemeral_ssh_key')],
                   check=True)
    name = 'stage-f2-%s-%s' % (arm, uuid.uuid4().hex[:6])
    payload = {'name': name, 'image': C.IMAGE, 'cloud': 'SECURE', 'disk': C.DISK_GB, 'startSsh': True,
               'gpu': {'id': C.GPU, 'count': 1, 'minCudaVersion': '12.8'}, 'ports': ['22/tcp'],
               'env': {'PUBLIC_KEY': (out/'ephemeral_ssh_key.pub').read_text().strip()}}
    print('creating ONE %s pod for F2 arm %s at quote $%.3f/h; hard stop %d min after creation'
          % (C.GPU, arm, hourly, L.CONFIG['hard_session_minutes']), flush=True)
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
    hard_stop = created + L.CONFIG['hard_session_minutes']*60
    soft_stop = hard_stop - L.ARCHIVE_RESERVE_SECONDS
    status = {'pod_id': pod_id, 'arm': arm, 'study': 'F2', 'quote_hourly': hourly, 'session': session_id, 'steps': []}
    stopped = threading.Event()
    def watchdog():
        if not stopped.wait(max(0, hard_stop-30-time.time())):
            print('local hard-stop watchdog terminating pod', flush=True)
            C.terminate(pod_id, key)
    threading.Thread(target=watchdog, daemon=True).start()
    client = tunnel = None
    try:
        client = C.wait_for_ssh(pod_id, key, out, soft_stop)
        client.run('mkdir -p /root/out && tar -xzf - -C /root', stdin=L.package(), timeout=300)
        client.run('umask 077 && cat > %s' % L.POD_KEY, stdin=(key+'\n').encode())
        client.run(C.background('env RUNPOD_POD_ID=%s python3 /root/stage_b/pod_guard.py --arm --config '
                                '/root/stage_e/guard_config.json --key-file %s --out %s'
                                % (shlex.quote(pod_id), L.POD_KEY, L.GUARD_OUT), '/root/out/guard.log'))
        if not C.wait_until(lambda: client.run('test -s %s/guard_ready.json' % L.GUARD_OUT, check=False).returncode == 0, 120, 5):
            raise RuntimeError('Pod-side guard did not arm; nothing else started')
        status['guard'] = json.loads(client.run('cat %s/guard_ready.json' % L.GUARD_OUT).stdout)
        client.run(C.background('bash /root/stage_e/v2_pod.sh %s' % shlex.quote(arm), '/root/out/v2_pod.log',
                                '/root/stage_e'))
        print('guard armed; v2_pod.sh started', flush=True)
        seen = 0
        while True:
            lines = L.pod_log(client).splitlines()
            if len(lines) >= seen:
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
        endpoint = 'http://127.0.0.1:%d/v1' % C.LOCAL_PORT
        if not health(endpoint, arm):
            raise RuntimeError('Serving health request failed')
        argv = [sys.executable, 'run_arm_f2.py', '--arm', arm, '--endpoint', endpoint, '--session', session_id,
                '--soft-stop-epoch', '%.0f' % soft_stop, '--run-approved']
        print('running F2', flush=True)
        code = subprocess.run(argv, cwd=HERE).returncode
        status['steps'].append({'phase': 'f2', 'exit_code': code})
    finally:
        stopped.set()
        try:
            if tunnel:
                tunnel.terminate()
            if client:
                status['log_fetch'], status['log_fetch_errors'] = L.fetch_logs(client, out)
                status.update(L.serving_provenance(out))
        except Exception as error:              # never block termination
            status['log_fetch_errors'] = status.get('log_fetch_errors', []) + [type(error).__name__]
        finally:
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
    parser.add_argument('--arm', choices=sorted(L.CONFIG['arms']))
    parser.add_argument('--key-file')
    parser.add_argument('--balance-key-file')
    parser.add_argument('--session')
    parser.add_argument('--approved-max-usd', type=float)
    args = parser.parse_args()
    _, cap = L.budget()
    if not (args.check_access or args.launch):
        print(json.dumps({'dry_run': True, 'api_calls': 0, 'cap_usd_per_arm': cap, 'arm_order': F['arm_order'],
                          'package_bytes': len(L.package())}, indent=2))
        return
    key = Path(args.key_file).read_text().strip()
    check = L.preflight(key, Path(args.balance_key_file).read_text().strip())
    print(json.dumps(check, indent=2), flush=True)
    if args.check_access:
        print('read-only access check complete; no pod created')
        return
    if not check['ok']:
        raise SystemExit('Preflight failed: existing pods, active spend, quote above ceiling or low balance')
    if not args.arm or args.approved_max_usd is None or args.approved_max_usd < cap:
        raise SystemExit('Pass --arm and --approved-max-usd with the ceiling approved in chat')
    if not F.get('allow_live_model_calls'):
        raise SystemExit('Live model calls are disabled in f_config.json')
    commit = check_frozen_and_pushed()
    if not args.session or not args.session.isalnum():
        parser.error('--session must be a new alphanumeric identifier')
    out = CACHE/'launch'/args.session
    if out.exists() or ((CACHE/'private'/args.session).exists() and any((CACHE/'private'/args.session).iterdir())):
        parser.error('Session already exists; a paid launch is never silently repeated')
    out.mkdir(parents=True, mode=0o700)
    (out/'launch.json').write_text(json.dumps({'frozen_commit': commit, 'arm': args.arm, 'study': 'F2',
        'preflight': check, 'approved_max_usd': args.approved_max_usd,
        'config_sha256': hashlib.sha256((HERE/'f_config.json').read_bytes()).hexdigest()}, indent=2)+'\n')
    launch(key, args.arm, check['quoted_hourly_with_disk'], args.session, out)


if __name__ == '__main__':
    main()
