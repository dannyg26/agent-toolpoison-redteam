"""F1 launcher: ONE pod for all three arms. Dry run by default; --check-access is read-only; --launch spends.

Reuses the frozen CTF v2 launcher's helpers (preflight, guard, log fetch, termination) with the F1 hard stop
(f1.hard_session_minutes). Uploads stage F's F1 files, arms the stage B guard first, starts f1_pod.sh
detached, and on every poll downloads any newly completed arm file (answers, judge scores) to
/home/capstone-study/stage_f/private/SESSION/, so a stop loses at most the arm in progress.
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
sys.path.insert(0, str(HERE.parent/'stage_e'))
sys.path.insert(0, str(HERE.parent/'stage_c'))
import launch_v2 as L  # noqa: E402

F = json.loads((HERE/'f_config.json').read_text())
L.CONFIG = dict(L.CONFIG, hard_session_minutes=F['f1']['hard_session_minutes'])
C = L.C
CACHE = Path('/home/capstone-study/stage_f')
POD_OUT = '/root/out/f1'
POLL_SECONDS = 30


def package():
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as tar:
        def add(name, data, mode=0o600):
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), mode
            tar.addfile(info, io.BytesIO(data))
        for name in ('pod_f1.py', 'f_config.json'):
            add('stage_f/'+name, (HERE/name).read_bytes().replace(b'\r\n', b'\n'))
        add('stage_f/f1_pod.sh', (HERE/'f1_pod.sh').read_bytes().replace(b'\r\n', b'\n'), 0o700)
        add('stage_f/v2_config.json', (HERE.parent/'stage_e/v2_config.json').read_bytes())
        for name in ('sr_judge.py', 'judge_templates.json'):
            add('stage_f/'+name, (HERE.parent/name).read_bytes().replace(b'\r\n', b'\n'))
        add('stage_f/items_f1.jsonl', (CACHE/'items_f1.jsonl').read_bytes())
        add('stage_e/guard_config.json', json.dumps(L.guard_config()).encode())
        add('stage_b/pod_guard.py', (HERE.parent/'stage_b/pod_guard.py').read_bytes().replace(b'\r\n', b'\n'))
    return stream.getvalue()


def fetch_completed(client, session, have):
    """Download every arm/judge file whose .done marker exists and that we do not have yet."""
    listing = client.run('ls %s 2>/dev/null' % POD_OUT, check=False, timeout=60).stdout.decode().split()
    for marker in [n for n in listing if n.endswith('.done')]:
        stem = marker[:-len('.done')]
        if stem in have:
            continue
        data = client.run('cat %s/%s.jsonl' % (POD_OUT, shlex.quote(stem)), check=False, timeout=300).stdout
        if not data:
            continue
        expected = client.run('cat %s/%s' % (POD_OUT, shlex.quote(marker)), check=False, timeout=60).stdout.decode().strip()
        if not stem.startswith('judge_') and hashlib.sha256(data).hexdigest() != expected:
            continue                                     # partial transfer; retry next poll
        (session/(stem+'.jsonl')).write_bytes(data)
        have.add(stem)
        print('fetched', stem, flush=True)


def check_frozen_and_pushed():
    from freeze_f import check_frozen_and_pushed as check   # never import launch_f2 (it sets its own cap)
    return check()


def launch(key, hourly, session_id, out):
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'stage-f1', '-f', str(out/'ephemeral_ssh_key')],
                   check=True)
    name = 'stage-f1-%s' % uuid.uuid4().hex[:6]
    payload = {'name': name, 'image': C.IMAGE, 'cloud': 'SECURE', 'disk': C.DISK_GB, 'startSsh': True,
               'gpu': {'id': C.GPU, 'count': 1, 'minCudaVersion': '12.8'}, 'ports': ['22/tcp'],
               'env': {'PUBLIC_KEY': (out/'ephemeral_ssh_key.pub').read_text().strip()}}
    print('creating ONE %s pod for F1 at quote $%.3f/h; hard stop %d min after creation'
          % (C.GPU, hourly, L.CONFIG['hard_session_minutes']), flush=True)
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
    status = {'pod_id': pod_id, 'study': 'F1', 'quote_hourly': hourly, 'session': session_id}
    stopped = threading.Event()
    def watchdog():
        if not stopped.wait(max(0, hard_stop-30-time.time())):
            print('local hard-stop watchdog terminating pod', flush=True)
            C.terminate(pod_id, key)
    threading.Thread(target=watchdog, daemon=True).start()
    session = CACHE/'private'/session_id
    session.mkdir(parents=True, exist_ok=True, mode=0o700)
    have, client = set(), None
    try:
        client = C.wait_for_ssh(pod_id, key, out, soft_stop)
        client.run('mkdir -p /root/out && tar -xzf - -C /root', stdin=package(), timeout=300)
        client.run('umask 077 && cat > %s' % L.POD_KEY, stdin=(key+'\n').encode())
        client.run(C.background('env RUNPOD_POD_ID=%s python3 /root/stage_b/pod_guard.py --arm --config '
                                '/root/stage_e/guard_config.json --key-file %s --out %s'
                                % (shlex.quote(pod_id), L.POD_KEY, L.GUARD_OUT), '/root/out/guard.log'))
        if not C.wait_until(lambda: client.run('test -s %s/guard_ready.json' % L.GUARD_OUT, check=False).returncode == 0, 120, 5):
            raise RuntimeError('Pod-side guard did not arm; nothing else started')
        status['guard'] = json.loads(client.run('cat %s/guard_ready.json' % L.GUARD_OUT).stdout)
        client.run(C.background('bash /root/stage_f/f1_pod.sh', '/root/out/f1_pod.log', '/root/stage_f'))
        print('guard armed; f1_pod.sh started', flush=True)
        seen = 0
        while time.time() < soft_stop:
            lines = client.run('cat %s/progress.log 2>/dev/null' % POD_OUT, check=False, timeout=60).stdout.decode().splitlines()
            if len(lines) >= seen:
                for line in lines[seen:]:
                    print('pod:', line, flush=True)
                seen = len(lines)
            try:
                fetch_completed(client, session, have)
            except Exception as error:
                print('fetch retry later:', type(error).__name__, flush=True)
            if any(l.endswith('ALL_DONE') or 'DRIVER_EXIT' in l or 'install FAILED' in l for l in lines):
                fetch_completed(client, session, have)
                break
            time.sleep(POLL_SECONDS)
        status['fetched'] = sorted(have)
    finally:
        stopped.set()
        try:
            if client:
                status['log_fetch'], status['log_fetch_errors'] = L.fetch_logs(client, out)
                data = client.run('cat %s/progress.log %s/pip-freeze.txt 2>/dev/null' % (POD_OUT, POD_OUT),
                                  check=False, timeout=60).stdout
                (out/'f1_pod_progress_and_env.txt').write_bytes(data)
        except Exception as error:              # never block termination
            status['log_fetch_errors'] = status.get('log_fetch_errors', []) + [type(error).__name__]
        finally:
            status['terminated'] = C.terminate(pod_id, key)
        status['elapsed_minutes_from_creation'] = round((time.time()-created)/60, 2)
        status['maximum_quoted_spend_before_tax'] = round((time.time()-created)/3600*hourly, 3)
        (out/'run_status.json').write_text(json.dumps(status, indent=2)+'\n')
        print(json.dumps({k: status.get(k) for k in ('pod_id', 'terminated', 'fetched', 'elapsed_minutes_from_creation',
                                                     'maximum_quoted_spend_before_tax')}), flush=True)
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
    _, cap = L.budget()
    if not (args.check_access or args.launch):
        print(json.dumps({'dry_run': True, 'api_calls': 0, 'cap_usd': cap, 'package_bytes': len(package())}, indent=2))
        return
    key = Path(args.key_file).read_text().strip()
    check = L.preflight(key, Path(args.balance_key_file).read_text().strip())
    print(json.dumps(check, indent=2), flush=True)
    if args.check_access:
        print('read-only access check complete; no pod created')
        return
    if not check['ok']:
        raise SystemExit('Preflight failed: existing pods, active spend, quote above ceiling or low balance')
    if args.approved_max_usd is None or args.approved_max_usd < cap:
        raise SystemExit('Pass --approved-max-usd with the ceiling approved in chat')
    if not F.get('allow_live_model_calls'):
        raise SystemExit('Live model calls are disabled in f_config.json')
    commit = check_frozen_and_pushed()
    if not args.session or not args.session.isalnum():
        parser.error('--session must be a new alphanumeric identifier')
    out = CACHE/'launch'/args.session
    if out.exists() or (CACHE/'private'/args.session).exists():
        parser.error('Session already exists; a paid launch is never silently repeated')
    out.mkdir(parents=True, mode=0o700)
    (out/'launch.json').write_text(json.dumps({'frozen_commit': commit, 'study': 'F1', 'preflight': check,
        'approved_max_usd': args.approved_max_usd,
        'config_sha256': hashlib.sha256((HERE/'f_config.json').read_bytes()).hexdigest()}, indent=2)+'\n')
    launch(key, check['quoted_hourly_with_disk'], args.session, out)


if __name__ == '__main__':
    main()
