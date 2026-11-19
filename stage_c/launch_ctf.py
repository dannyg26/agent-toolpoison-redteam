"""Stage C single-pod launcher. Dry run by default; --check-access is read-only; --launch spends.

Runs in the WSL host that owns the CTF Docker environments and the private cache. It rents ONE
RunPod A100 pod, arms the unmodified stage B pod guard on it, serves one model at a time with
inference_server.py behind an SSH tunnel to 127.0.0.1:18000, and runs the frozen development checks
and test blocks from this host with run_smoke.py and run_phase.py. The pod is terminated in a
`finally` block; the pod-side guard is the independent backup.

Keys are read from private files and never printed, logged or passed as command arguments.
No payment, top-up, persistent volume, retry rental or second pod is ever created.
"""
from __future__ import annotations

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
import urllib.request
import uuid

from budget import calculate
from environment import CACHE, HERE

API = 'https://api.runpod.io/v2'
GRAPHQL = 'https://api.runpod.io/graphql'
GPU = 'NVIDIA A100-SXM4-80GB'
IMAGE = 'runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404'
DISK_GB = 200
LOCAL_PORT = 18000
POD_ROOT = '/root/ctf'
GUARD_OUT = '/root/out/stage_c_guard'
POD_KEY = '/root/guard.key'
# Each model is served for the development check and its first block; order follows the protocol.
STEPS = [('serve', 'main'), ('smoke', 'main'), ('phase', 'main-1'),
         ('serve', 'control'), ('smoke', 'control'), ('phase', 'control-1'), ('phase', 'control-2'),
         ('serve', 'main'), ('phase', 'main-2')]
MODEL_LOAD_TIMEOUT = 25 * 60
ARCHIVE_RESERVE_SECONDS = 5 * 60


def api(method, path, key, body=None, timeout=30):
    request = urllib.request.Request(API+path, method=method,
        headers={'Authorization': 'Bearer '+key, 'Content-Type': 'application/json'},
        data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return None if response.status == 204 else json.load(response)


def read_balance(balance_key):
    body = json.dumps({'query': 'query { myself { clientBalance currentSpendPerHr } }'}).encode()
    request = urllib.request.Request(GRAPHQL, data=body, method='POST',
        headers={'Authorization': 'Bearer '+balance_key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        me = json.load(response)['data']['myself']
    return float(me['clientBalance']), float(me['currentSpendPerHr'])


def quoted_hourly(gpu_price):
    return gpu_price + DISK_GB*0.10/720      # temporary disk, $0.10/GB/month, 720-hour month


def preflight(key, balance_key, config):
    """Read-only: no pods exist, nothing is spending, quote within the cap, balance covers the cap."""
    budget = calculate(config)
    rows = api('GET', '/pods', key)
    rows = rows if isinstance(rows, list) else rows.get('pods', [])
    gpu = next(x for x in api('GET', '/catalog/gpus', key)['gpus'] if x['id'] == GPU)
    hourly = quoted_hourly(float(gpu['price']['secure']))
    balance, spend = read_balance(balance_key)
    cap = float(budget['capped_additional_usd_including_reserve'])
    result = {'existing_pods': len(rows), 'gpu': GPU, 'secure_gpu_price': gpu['price']['secure'],
              'quoted_hourly_with_disk': round(hourly, 4),
              'hourly_ceiling': float(config['maximum_hourly_usd_including_disk']),
              'balance_usd': round(balance, 4), 'current_spend_per_hour': spend,
              'maximum_additional_spend_usd': cap,
              'cost_at_quote_for_full_session_usd': round(hourly*config['hard_session_minutes']/60, 4)}
    result['ok'] = (not rows and spend == 0 and hourly <= result['hourly_ceiling'] and balance >= cap)
    return result


def check_frozen_and_pushed():
    from freeze_tools import verify
    snapshot = json.loads((HERE/'ctf_freeze.json').read_text())
    verify(snapshot)
    git = ['git', '-c', 'safe.directory=*', '-C', str(HERE)]
    if subprocess.run(git+['status', '--porcelain', '--', '.'], capture_output=True, text=True,
                      check=True).stdout.strip():
        raise SystemExit('stage_c has uncommitted changes; commit and push the freeze first')
    head = subprocess.run(git+['rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    remote = subprocess.run(git+['branch', '-r', '--contains', head], capture_output=True, text=True,
                            check=True).stdout.strip()
    if not remote:
        raise SystemExit('The frozen commit is not on any remote branch; push it before launch')
    return head


# Only what the pod-side guard and model server import. Grading, flag-patching, challenge and
# controller code never leave this host.
POD_FILES = ['inference_server.py', 'guard_adapter.py', 'budget.py', 'freeze_tools.py', 'environment.py',
             'study_config.json', 'ctf_freeze.json']


def package_source():
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as tar:
        for arcname, path in [('stage_c/'+n, HERE/n) for n in POD_FILES] + [
                ('stage_b/pod_guard.py', HERE.parent/'stage_b/pod_guard.py')]:
            data = path.read_bytes().replace(b'\r\n', b'\n')
            info = tarfile.TarInfo(arcname)
            info.size, info.mode = len(data), 0o600
            tar.addfile(info, io.BytesIO(data))
    return stream.getvalue()


class Pod:
    def __init__(self, out, host, port):
        self.out, self.host, self.port = out, host, port
        self.base = ['-i', str(out/'ephemeral_ssh_key'), '-o', 'IdentitiesOnly=yes',
                     '-o', 'StrictHostKeyChecking=accept-new',
                     '-o', 'UserKnownHostsFile='+str(out/'known_hosts'),
                     '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=15',
                     '-o', 'ServerAliveCountMax=4', '-p', str(port)]

    def run(self, command, stdin=None, timeout=120, check=True):
        result = subprocess.run(['ssh', *self.base, 'root@'+self.host, command], input=stdin,
                                capture_output=True, timeout=timeout)
        if check and result.returncode:
            raise RuntimeError('Pod command failed (exit %d): %s' % (result.returncode, command[:120]))
        return result

    def tunnel(self):
        return subprocess.Popen(['ssh', *self.base, '-N', '-o', 'ExitOnForwardFailure=yes',
                                 '-L', '127.0.0.1:%d:127.0.0.1:8000' % LOCAL_PORT, 'root@'+self.host],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_for_ssh(pod_id, key, out, stop_at):
    while time.time() < stop_at:
        pod = api('GET', '/pods/'+pod_id, key)
        direct = (pod.get('ssh') or {}).get('direct')
        if not direct:
            port = next((p for p in (pod.get('runtime') or {}).get('ports', []) or []
                         if p.get('privatePort', p.get('private')) == 22 and p.get('ip')
                         and p.get('publicPort', p.get('public'))), None)
            if port:
                direct = {'host': port['ip'], 'port': port.get('publicPort', port.get('public'))}
        if direct:
            client = Pod(out, direct['host'], direct['port'])
            try:
                if client.run('true', timeout=30, check=False).returncode == 0:
                    return client
            except subprocess.TimeoutExpired:
                pass
        time.sleep(10)
    raise TimeoutError('Pod SSH never became available before the deadline')


def wait_until(predicate, timeout, interval=10):
    stop = time.time()+timeout
    while time.time() < stop:
        if predicate():
            return True
        time.sleep(interval)
    return False


def background(command, log, workdir=None):
    """Start a detached pod process that holds none of the SSH session's pipes.

    The whole chain sits inside a subshell so `&` backgrounds only the inner command and the
    subshell exits at once. Any `a && b &` form hangs, inside parentheses too: the backgrounded list runs
    in a subshell that keeps SSH's stdout open (leases 1 and 2).
    """
    prefix = 'cd %s || exit 1; ' % shlex.quote(workdir) if workdir else ''
    return '(%snohup %s > %s 2>&1 < /dev/null &)' % (prefix, command, shlex.quote(log))


# Bracketed first letter: the pattern never matches the remote shell running pkill itself.
STOP_VLLM = ("pkill -f '[v]llm.entrypoints.openai.api_server'; sleep 5; "
             "pkill -9 -f '[v]llm.entrypoints.openai.api_server'; true")


def setup_pod(pod, key, pod_id, hourly, config):
    pod.run('mkdir -p %s /root/out && tar -xzf - -C %s' % (POD_ROOT, POD_ROOT), stdin=package_source())
    pod.run('umask 077 && cat > %s' % POD_KEY, stdin=(key+'\n').encode())
    # Guard first, before any package or model download.
    pod.run(background('env RUNPOD_POD_ID=%s python3 guard_adapter.py --arm --key-file %s --out %s '
                       '--verified-all-in-hourly %.4f' % (shlex.quote(pod_id), POD_KEY, GUARD_OUT, hourly),
                       '/root/out/guard.log', POD_ROOT+'/stage_c'))
    if not wait_until(lambda: pod.run('test -s %s/guard_ready.json' % GUARD_OUT, check=False).returncode == 0,
                      120, 5):
        raise RuntimeError('Pod-side guard did not arm; no downloads started')
    ready = json.loads(pod.run('cat %s/guard_ready.json' % GUARD_OUT).stdout)
    # Package install, then both checkpoints in protocol order, in the background.
    downloads = ' && '.join(
        'python3 -c %s && touch /root/out/downloaded-%s' % (shlex.quote(
            'from huggingface_hub import snapshot_download; snapshot_download(%r, revision=%r)'
            % (config[c+'_model'], config[c+'_revision'])), c) for c in ('main', 'control'))
    pod.run(background('sh -c %s' % shlex.quote(
        'python3 -m pip install -q vllm==0.33.0 hf_transfer && touch /root/out/installed && '
        'export HF_HUB_ENABLE_HF_TRANSFER=1 && ' + downloads), '/root/out/setup.log'))
    return ready


def serve(pod, condition, pod_id, hourly, count):
    pod.run(STOP_VLLM, timeout=60)
    if not wait_until(lambda: pod.run('test -e /root/out/downloaded-'+condition, check=False).returncode == 0,
                      MODEL_LOAD_TIMEOUT):
        raise TimeoutError('Checkpoint download did not finish in time: '+condition)
    pod.run(background('env RUNPOD_POD_ID=%s HF_HUB_OFFLINE=1 python3 inference_server.py --condition %s '
                       '--run --guard-ready %s/guard_ready.json --key-file %s --verified-all-in-hourly %.4f'
                       % (shlex.quote(pod_id), condition, GUARD_OUT, POD_KEY, hourly),
                       '/root/out/vllm-%s-%d.log' % (condition, count), POD_ROOT+'/stage_c'))
    served = 'csc-'+condition
    def healthy():
        result = pod.run('curl -sf --max-time 5 http://127.0.0.1:8000/v1/models', check=False, timeout=30)
        return result.returncode == 0 and served in result.stdout.decode(errors='replace')
    if not wait_until(healthy, MODEL_LOAD_TIMEOUT):
        raise TimeoutError('vLLM did not become healthy: '+condition)


def local(script, session, soft_stop, condition=None, phase=None):
    argv = [sys.executable, script, '--endpoint', 'http://127.0.0.1:%d/v1' % LOCAL_PORT,
            '--session', session, '--soft-stop-epoch', '%.0f' % soft_stop, '--run-approved']
    argv += ['--condition', condition] if condition else ['--phase', phase]
    print('running', script, condition or phase, flush=True)
    return subprocess.run(argv, cwd=HERE).returncode


def fetch_logs(pod, out):
    try:
        listing = pod.run('ls /root/out', check=False, timeout=30).stdout.decode().split()
        for name in listing:
            if name.endswith('.log') or name.endswith('.json'):
                data = pod.run('tail -c 2000000 /root/out/'+shlex.quote(name), check=False, timeout=60).stdout
                (out/'pod_logs').mkdir(exist_ok=True)
                (out/'pod_logs'/name).write_bytes(data)
    except Exception as error:      # logs are best effort; never block termination
        print('pod log download failed:', type(error).__name__, flush=True)


def terminate(pod_id, key):
    for _ in range(12):
        try:
            api('DELETE', '/pods/'+pod_id, key)
            return True
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return True
        except (OSError, ValueError):
            pass
        time.sleep(5)
    return False


def launch(key, config, hourly, session, out):
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'ctf-stage-c',
                    '-f', str(out/'ephemeral_ssh_key')], check=True)
    public = (out/'ephemeral_ssh_key.pub').read_text().strip()
    name = 'ctf-stage-c-'+uuid.uuid4().hex[:8]
    # Same v2 creation schema the stage B launches used; the image's own start script runs sshd.
    payload = {'name': name, 'image': IMAGE, 'cloud': 'SECURE', 'disk': DISK_GB, 'startSsh': True,
               'gpu': {'id': GPU, 'count': 1, 'minCudaVersion': '12.8'}, 'ports': ['22/tcp'],
               'env': {'PUBLIC_KEY': public}}
    print('creating ONE %s pod at quote $%.3f/h; hard stop %d minutes after creation'
          % (GPU, hourly, config['hard_session_minutes']), flush=True)
    requested = time.time()
    try:
        pod = api('POST', '/pods', key, payload)          # never retried blindly
    except urllib.error.HTTPError as error:
        raise SystemExit('RunPod refused allocation: HTTP %d; no retry' % error.code) from None
    except (OSError, ValueError):
        rows = api('GET', '/pods', key)
        found = [x for x in (rows if isinstance(rows, list) else rows.get('pods', [])) if x.get('name') == name]
        if len(found) != 1:
            raise RuntimeError('Creation response uncertain; no second creation attempted') from None
        pod = found[0]
    pod_id = pod['id']
    status = {'pod_id': pod_id, 'name': name, 'quote_hourly': hourly, 'launch_requested_epoch': requested,
              'session': session, 'steps': []}
    from guard_adapter import guard
    # Conservative: the pod's own creation time (or our request time) starts the clock, like the guard.
    created = guard.parse_created(pod) if pod.get('createdAt') else requested
    hard_stop = created + config['hard_session_minutes']*60
    soft_stop = hard_stop - ARCHIVE_RESERVE_SECONDS
    stop_event = threading.Event()
    def watchdog():
        # Local backup timer: terminates at the hard stop even if a step hangs.
        if not stop_event.wait(max(0, hard_stop-30-time.time())):
            print('local hard-stop watchdog terminating pod', flush=True)
            terminate(pod_id, key)
    threading.Thread(target=watchdog, daemon=True).start()
    tunnel = pod_client = None
    serves = 0
    try:
        pod_client = wait_for_ssh(pod_id, key, out, soft_stop)
        status['guard'] = setup_pod(pod_client, key, pod_id, hourly, config)
        for kind, value in STEPS:
            if time.time() >= soft_stop:
                status['steps'].append({'step': kind+':'+value, 'result': 'not_started_soft_stop'})
                break
            if kind == 'serve':
                if tunnel:
                    tunnel.terminate()
                serves += 1
                started = time.time()
                serve(pod_client, value, pod_id, hourly, serves)
                tunnel = pod_client.tunnel()
                time.sleep(3)
                if tunnel.poll() is not None:
                    raise RuntimeError('SSH tunnel to the model server failed')
                status['steps'].append({'step': 'serve:'+value, 'seconds': round(time.time()-started)})
                continue
            script = 'run_smoke.py' if kind == 'smoke' else 'run_phase.py'
            code = local(script, session, soft_stop, condition=value if kind == 'smoke' else None,
                         phase=value if kind == 'phase' else None)
            status['steps'].append({'step': kind+':'+value, 'exit_code': code})
            if code:
                print('step failed; no further collection in this session', flush=True)
                break
    finally:
        if tunnel:
            tunnel.terminate()
        if pod_client:
            fetch_logs(pod_client, out)
        stop_event.set()
        status['terminated'] = terminate(pod_id, key)
        status['elapsed_minutes_from_creation'] = round((time.time()-created)/60, 2)
        status['maximum_quoted_spend_before_tax'] = round((time.time()-created)/3600*hourly, 3)
        (out/'run_status.json').write_text(json.dumps(status, indent=2)+'\n')
        print(json.dumps({k: status[k] for k in ('pod_id', 'terminated', 'elapsed_minutes_from_creation',
                                                 'maximum_quoted_spend_before_tax')}), flush=True)
        if not status['terminated']:
            raise RuntimeError('Termination not confirmed; check the RunPod console now. Guard is the backup.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check-access', action='store_true', help='read-only API checks; never creates a pod')
    mode.add_argument('--launch', action='store_true')
    parser.add_argument('--key-file')
    parser.add_argument('--balance-key-file')
    parser.add_argument('--session')
    parser.add_argument('--approved-max-usd', type=float,
                        help='the spend ceiling the user approved in chat; must cover the computed cap')
    args = parser.parse_args()
    config = json.loads((HERE/'study_config.json').read_text())
    budget = calculate(config)
    if not (args.check_access or args.launch):
        print(json.dumps({'dry_run': True, 'api_calls': 0, 'gpu': GPU, 'steps': STEPS, 'budget': budget}, indent=2))
        return
    if not (args.key_file and args.balance_key_file):
        parser.error('--key-file and --balance-key-file are required; never pass key values as arguments')
    key = Path(args.key_file).expanduser().read_text(encoding='utf-8').strip()
    balance_key = Path(args.balance_key_file).expanduser().read_text(encoding='utf-8').strip()
    check = preflight(key, balance_key, config)
    print(json.dumps(check, indent=2), flush=True)
    if args.check_access:
        print('read-only access check complete; no pod created')
        return
    if not check['ok']:
        raise SystemExit('Preflight failed: existing pods, active spend, quote above ceiling or low balance')
    if args.approved_max_usd is None or args.approved_max_usd < check['maximum_additional_spend_usd']:
        raise SystemExit('Pass --approved-max-usd with the ceiling approved in chat')
    if not config.get('allow_live_model_calls'):
        raise SystemExit('Live model calls are disabled in study_config.json')
    commit = check_frozen_and_pushed()
    if not args.session or not args.session.isalnum() or len(args.session) > 40:
        parser.error('--session must be a new alphanumeric identifier')
    out = CACHE/'launch'/args.session
    if out.exists() or (CACHE/'private'/args.session).exists():
        parser.error('Session already exists; a paid launch is never silently repeated')
    out.mkdir(parents=True, mode=0o700)
    (out/'launch.json').write_text(json.dumps({'frozen_commit': commit, 'preflight': check,
        'approved_max_usd': args.approved_max_usd,
        'config_sha256': hashlib.sha256((HERE/'study_config.json').read_bytes()).hexdigest()}, indent=2)+'\n')
    launch(key, config, check['quoted_hourly_with_disk'], args.session, out)
    print('collection session finished; analyse with analyze_ctf.py on',
          CACHE/'private'/args.session/'results.jsonl', flush=True)


if __name__ == '__main__':
    main()
