"""Run one arm of CTF v2 (development or test phase) from the WSL host, three trials at a time.

The model is reached through an SSH tunnel on 127.0.0.1 (launch_v2.py). Every trial has its own sandbox,
fresh secret, seed (from SHA-256 of the task ID; recorded, but trials are not bit-reproducible under
concurrent batching) and trace file; its result row is appended and fsynced as soon as it ends. A recorded
trial is never retried. Before the trial clock starts, the sandbox must pass the base health probe and the
reachability gate (EnvironmentV2.wait_reachable); a target that never opens is the infrastructure failure
`target_unreachable`. A trial is not started unless its full wall cap plus START_RESERVE_SECONDS (300 s:
sandbox create/start/health <= 200 s, reachability gate about 67 s worst case, teardown <= 30 s) fits before the soft
stop; later trials are unobserved. Two infrastructure failures in one phase stop the phase. Every trace
event carries `trials_in_flight` (trials of this phase running at that moment).

Development gate (infrastructure only; development_gate()): the test phase does not start if any
development trial is an infrastructure failure or not started, or if any development trial got no
completed model reply (transport/serving health; a request cut off by the trial's own cap is discounted). Model behaviour, including refusing or never
calling a tool on every development task, never blocks the test phase; parsed tool calls are recorded as
an outcome only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'stage_c'))
from endpoint_client import EndpointClient  # noqa: E402
from environment_v2 import EnvironmentV2, TargetUnreachable, task_prompt  # noqa: E402
from trajectory_v2 import ExactGrader, run_trajectory  # noqa: E402

CACHE = Path('/home/capstone-study/stage_e')
CONFIG = json.loads((HERE/'v2_config.json').read_text())
START_RESERVE_SECONDS = 300
_IN_FLIGHT = {'n': 0}
_IN_FLIGHT_LOCK = threading.Lock()


def development_gate(rows):
    """(ok, reason). Infrastructure/interface check only; model behaviour never fails it."""
    infra = sorted(r['task_id'] for r in rows if r['status'] in ('infrastructure_failure', 'not_started'))
    if infra:
        return False, 'development trial(s) not completed for infrastructure reasons: %s' % infra
    def completed_replies(row):
        # A request cut off by the trial's own time cap leaves usage incomplete; that is model behaviour,
        # not a fault, so only the in-flight request is discounted.
        requests = row.get('model_requests', 0)
        return requests if row.get('generated_token_usage_complete', False) else requests - 1
    unhealthy = sorted(r['task_id'] for r in rows if completed_replies(r) < 1)
    if unhealthy:
        return False, 'development trial(s) without a complete model reply (serving/transport): %s' % unhealthy
    return True, 'ok'


def ordered(tasks):
    return sorted(tasks, key=lambda t: hashlib.sha256(('ctf_v2:'+t['id']).encode()).hexdigest())


def task_seed(task_id):
    return int(hashlib.sha256(task_id.encode()).hexdigest()[:8], 16)


def require_freeze():
    from freeze_v2 import verify
    verify(json.loads((HERE/'v2_freeze.json').read_text()))


class Recorder:
    def __init__(self, session):
        self.session, self.lock = session, threading.Lock()
        self.results = session/'results.jsonl'

    def existing(self):
        if not self.results.exists():
            return set()
        return {(json.loads(l)['task_id'], json.loads(l)['arm'], json.loads(l)['phase'])
                for l in self.results.read_text().splitlines() if l.strip()}

    def append(self, row):
        with self.lock, self.results.open('a') as stream:
            stream.write(json.dumps(row)+'\n')
            stream.flush()
            os.fsync(stream.fileno())


def run_trial(task, arm, phase, endpoint, session, recorder, soft_stop, wall_cap, make_client):
    if time.time() + wall_cap + START_RESERVE_SECONDS >= soft_stop:
        return {'task_id': task['id'], 'arm': arm, 'phase': phase, 'status': 'not_started', 'solved': None,
                'reason': 'soft_stop_reserve'}
    trace = session/('%s-%s-%s-trace.jsonl' % (task['id'], arm, phase))
    lock = threading.Lock()
    def record(event):
        event = dict(event, trials_in_flight=_IN_FLIGHT['n'])
        with lock, trace.open('a') as stream:
            stream.write(json.dumps(event)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
    config = dict(CONFIG, wall_cap_seconds=wall_cap, seed=task_seed(task['id']))
    result = None
    with _IN_FLIGHT_LOCK:
        _IN_FLIGHT['n'] += 1
    try:
        with EnvironmentV2(task['id'], discovery=(phase == 'development')) as env:
            env.wait_healthy()
            try:
                attempts = env.wait_reachable()
            except TargetUnreachable as error:
                record({'kind': 'reachability_gate', 'attempts': error.attempts, 'open': False})
                raise
            record({'kind': 'reachability_gate', 'attempts': attempts, 'open': True})
            record({'kind': 'private_checker_reference', 'expected_flag': env.expected_flag})
            prompt = task_prompt(env.metadata, task.get('category') or task['id'].split('-')[1])
            result = run_trajectory(make_client(config), env, ExactGrader(env.expected_flag), prompt, config,
                                    record=record)
    except Exception as error:
        record({'kind': 'environment_error', 'error': str(error)})
        if result is None:
            result = {'status': 'infrastructure_failure', 'solved': None,
                      'reason': 'target_unreachable' if isinstance(error, TargetUnreachable) else 'environment_failure'}
        else:
            result['environment_cleanup_error'] = True
    finally:
        with _IN_FLIGHT_LOCK:
            _IN_FLIGHT['n'] -= 1
    result.update(task_id=task['id'], arm=arm, phase=phase, model=CONFIG['arms'][arm]['model'],
                  revision=CONFIG['arms'][arm]['revision'])
    recorder.append(result)
    print(task['id'], arm, phase, result['status'], result.get('reason'), flush=True)
    return result


def run_phase(arm, phase, endpoint, session, soft_stop, make_client=None):
    if phase == 'development':
        tasks = json.loads((HERE.parent/'stage_c/development_manifest.json').read_text())['tasks']
        wall_cap = CONFIG['development_wall_cap_seconds']
    else:
        tasks = json.loads((HERE.parent/'stage_c/challenge_manifest.json').read_text())['tasks']
        wall_cap = CONFIG['wall_cap_seconds']
    if make_client is None:
        def make_client(config):
            return EndpointClient(endpoint, 'csc-'+arm, config, approved=True)
    recorder = Recorder(session)
    done = recorder.existing()
    todo = [t for t in ordered(tasks) if (t['id'], arm, phase) not in done]
    if len(todo) != len(tasks):
        raise ValueError('Some planned trials already have results; no automatic reattempt')
    failures = []
    stop = threading.Event()
    def guarded(task):
        if stop.is_set():
            return {'task_id': task['id'], 'arm': arm, 'phase': phase, 'status': 'not_started',
                    'solved': None, 'reason': 'phase_stopped'}
        row = run_trial(task, arm, phase, endpoint, session, recorder, soft_stop, wall_cap, make_client)
        if row['status'] == 'infrastructure_failure':
            failures.append(task['id'])
            if len(failures) >= 2:
                stop.set()
        return row
    with ThreadPoolExecutor(max_workers=CONFIG['concurrency']) as pool:
        rows = list(pool.map(guarded, todo))
    for row in rows:
        if row['status'] == 'not_started':
            recorder.append(dict(row, model=CONFIG['arms'][arm]['model'], revision=CONFIG['arms'][arm]['revision']))
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--arm', required=True, choices=sorted(CONFIG['arms']))
    parser.add_argument('--phase', required=True, choices=['development', 'test'])
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--session', required=True)
    parser.add_argument('--soft-stop-epoch', type=float, required=True)
    parser.add_argument('--run-approved', action='store_true')
    args = parser.parse_args()
    if not args.run_approved or not CONFIG.get('allow_live_model_calls'):
        raise PermissionError('Live collection is disabled')
    require_freeze()
    if not args.session.isalnum() or len(args.session) > 40:
        raise ValueError('Use a simple alphanumeric session identifier')
    session = CACHE/'private'/args.session
    session.mkdir(parents=True, exist_ok=True, mode=0o700)
    rows = run_phase(args.arm, args.phase, args.endpoint, session, args.soft_stop_epoch)
    if args.phase == 'development':
        ok, reason = development_gate(rows)
        (session/'development_gate.json').write_text(json.dumps({'arm': args.arm, 'ok': ok, 'reason': reason})+'\n')
        if not ok:
            raise SystemExit('Development infrastructure check failed (%s); test phase must not start' % reason)
    print('phase complete', args.arm, args.phase, flush=True)


if __name__ == '__main__':
    main()
