"""Reuse the tested pod-side termination guard with the CTF budget; dry-run by default."""
import argparse
import importlib.util
import json
import math
import re
from pathlib import Path
import subprocess
import sys
import time

from budget import calculate

HERE = Path(__file__).resolve().parent
GUARD_PATH = HERE.parent/'stage_b/pod_guard.py'
spec = importlib.util.spec_from_file_location('ctf_existing_pod_guard', GUARD_PATH)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def guard_config(config):
    calculate(config)
    return {'hourly_usd_including_disk': float(config['maximum_hourly_usd_including_disk']),
            'maximum_compute_usd': float(config['maximum_hourly_usd_including_disk']) *
                                   config['hard_session_minutes']/60,
            'maximum_session_minutes': config['hard_session_minutes']}


def verify_ready(ready, authenticated_pod, config, now, quoted_all_in_hourly):
    """Pod metadata must come from an authenticated GET, not the guard's own file."""
    quote = float(quoted_all_in_hourly)
    if not math.isfinite(quote) or quote <= 0 or quote > float(config['maximum_hourly_usd_including_disk']):
        raise ValueError('Current all-in quote exceeds the budget or is invalid')
    if not authenticated_pod.get('id') or ready.get('pod_id') != authenticated_pod.get('id'):
        raise ValueError('Guard identity mismatch')
    created = guard.parse_created(authenticated_pod)
    g = guard_config(config)
    wanted = guard.deadline(created, g['hourly_usd_including_disk'],
                            g['maximum_compute_usd'], g['maximum_session_minutes'])
    if abs(float(ready['deadline_epoch'])-wanted) > 5 or not created-60 <= now < wanted:
        raise ValueError('Guard deadline does not match authenticated creation time and CTF cap')
    return wanted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--arm', action='store_true')
    parser.add_argument('--key-file')
    parser.add_argument('--out', default='/root/out/stage_c_guard')
    parser.add_argument('--verified-all-in-hourly', type=float)
    args = parser.parse_args()
    config = json.loads((HERE/'study_config.json').read_text())
    g = guard_config(config)
    if not args.arm:
        print(json.dumps({'dry_run': True, 'cloud_api_calls': 0,
                          'guard_configuration': g, 'budget': calculate(config)}, indent=2))
        return
    if not args.key_file or args.verified_all_in_hourly is None:
        raise ValueError('A private key file and independently verified current quote are required')
    import os
    pod_id = os.environ.get('RUNPOD_POD_ID', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{5,80}', pod_id):
        raise ValueError('Armed mode must run inside the actual rented pod')
    keypath = Path(args.key_file)
    if keypath.stat().st_mode & 0o077:
        raise ValueError('Pod-side key file must have mode 600')
    key = keypath.read_text().strip()
    pod = guard.api_request('GET', pod_id, key)
    created = guard.parse_created(pod)
    deadline = guard.deadline(created, g['hourly_usd_including_disk'],
                              g['maximum_compute_usd'], g['maximum_session_minutes'])
    verify_ready({'pod_id': pod_id, 'deadline_epoch': deadline}, pod, config,
                  time.time(), args.verified_all_in_hourly)
    # The existing guard independently verifies this pod/key pair again and monitors a monotonic deadline.
    config_path = Path(args.out)/'ctf_guard_config.json'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(g)+'\n')
    subprocess.run([sys.executable, str(GUARD_PATH), '--arm', '--config', str(config_path),
                    '--key-file', str(keypath), '--out', args.out], check=True)


if __name__ == '__main__':
    main()
