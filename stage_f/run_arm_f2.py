"""F2: run one arm's malicious-framing trials (7 tasks x 2 repeats) on this host, three at a time.

Uses the frozen CTF v2 trajectory (trajectory_v2.run_trajectory) unchanged, except that its module-level
system prompt is replaced by framing_f2.SYSTEM_F2 for this process (run_trajectory reads it at call time).
Each trial: EnvironmentF2 sandbox with the generic alias, fresh secret, v2 reachability gate, framed task
prompt, seed SHA-256(task_id + '#' + repeat). Result rows are appended and fsynced per trial; a recorded
(task, repeat, arm) is never re-run. Two infrastructure failures stop the phase.
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
sys.path.insert(0, str(HERE.parent/'stage_e'))
sys.path.insert(0, str(HERE.parent/'stage_c'))
import trajectory_v2 as T  # noqa: E402
from endpoint_client import EndpointClient  # noqa: E402
from environment_f2 import EnvironmentF2  # noqa: E402
from environment_v2 import TargetUnreachable  # noqa: E402
from framing_f2 import SYSTEM_F2, task_prompt_f2  # noqa: E402

T.SYSTEM = SYSTEM_F2                       # the only harness change besides the prompt and alias
V2 = json.loads((HERE.parent/'stage_e/v2_config.json').read_text())
F = json.loads((HERE/'f_config.json').read_text())
CACHE = Path('/home/capstone-study/stage_f')
START_RESERVE_SECONDS = 300


def trial_seed(task_id, repeat):
    return int(hashlib.sha256(('%s#%d' % (task_id, repeat)).encode()).hexdigest()[:8], 16)


def planned_trials():
    order = sorted(F['f2']['tasks'], key=lambda t: hashlib.sha256(('stage_f2:'+t).encode()).hexdigest())
    return [(task, repeat) for repeat in range(1, F['f2']['repeats']+1) for task in order]


class Recorder:
    def __init__(self, session):
        self.lock, self.path = threading.Lock(), session/'results.jsonl'

    def existing(self):
        if not self.path.exists():
            return set()
        rows = [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()]
        return {(r['task_id'], r['repeat'], r['arm']) for r in rows}

    def append(self, row):
        with self.lock, self.path.open('a') as stream:
            stream.write(json.dumps(row)+'\n')
            stream.flush()
            os.fsync(stream.fileno())


def run_trial(task_id, repeat, arm, session, recorder, soft_stop, make_client):
    wall_cap = V2['wall_cap_seconds']
    base = {'task_id': task_id, 'repeat': repeat, 'arm': arm, 'framing': 'malicious',
            'model': V2['arms'][arm]['model'], 'revision': V2['arms'][arm]['revision']}
    if time.time() + wall_cap + START_RESERVE_SECONDS >= soft_stop:
        row = dict(base, status='not_started', solved=None, reason='soft_stop_reserve')
        recorder.append(row)
        return row
    trace = session/('%s-r%d-%s-trace.jsonl' % (task_id, repeat, arm))
    lock = threading.Lock()
    def record(event):
        with lock, trace.open('a') as stream:
            stream.write(json.dumps(event)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
    config = dict(V2, wall_cap_seconds=wall_cap, seed=trial_seed(task_id, repeat))
    result = None
    try:
        with EnvironmentF2(task_id) as env:
            env.wait_healthy()
            try:
                attempts = env.wait_reachable()
            except TargetUnreachable as error:
                record({'kind': 'reachability_gate', 'attempts': error.attempts, 'open': False})
                raise
            record({'kind': 'reachability_gate', 'attempts': attempts, 'open': True})
            record({'kind': 'private_checker_reference', 'expected_flag': env.expected_flag})
            prompt = task_prompt_f2(env.metadata, task_id.split('-')[1])
            result = T.run_trajectory(make_client(config), env, T.ExactGrader(env.expected_flag), prompt, config,
                                      record=record)
    except Exception as error:
        record({'kind': 'environment_error', 'error': str(error)})
        if result is None:
            result = {'status': 'infrastructure_failure', 'solved': None,
                      'reason': 'target_unreachable' if isinstance(error, TargetUnreachable) else 'environment_failure'}
        else:
            result['environment_cleanup_error'] = True
    row = dict(result, **base)
    recorder.append(row)
    print(task_id, 'r%d' % repeat, arm, row['status'], row.get('reason'), flush=True)
    return row


def run_phase(arm, endpoint, session, soft_stop, make_client=None):
    if make_client is None:
        def make_client(config):
            return EndpointClient(endpoint, 'csc-'+arm, config, approved=True)
    recorder = Recorder(session)
    done = recorder.existing()
    todo = [(t, r) for t, r in planned_trials() if (t, r, arm) not in done]
    if len(todo) != len(planned_trials()):
        raise ValueError('Some planned F2 trials already have results; no automatic reattempt')
    failures, stop = [], threading.Event()
    def guarded(trial):
        if stop.is_set():
            row = {'task_id': trial[0], 'repeat': trial[1], 'arm': arm, 'framing': 'malicious',
                   'status': 'not_started', 'solved': None, 'reason': 'phase_stopped'}
            recorder.append(row)
            return row
        row = run_trial(trial[0], trial[1], arm, session, recorder, soft_stop, make_client)
        if row['status'] == 'infrastructure_failure':
            failures.append(trial)
            if len(failures) >= 2:
                stop.set()
        return row
    with ThreadPoolExecutor(max_workers=V2['concurrency']) as pool:
        return list(pool.map(guarded, todo))


def require_freeze():
    from freeze_f import verify
    verify(json.loads((HERE/'f_freeze.json').read_text()))   # also re-verifies the CTF v2 freeze


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--arm', required=True, choices=sorted(V2['arms']))
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--session', required=True)
    parser.add_argument('--soft-stop-epoch', type=float, required=True)
    parser.add_argument('--run-approved', action='store_true')
    args = parser.parse_args()
    if not args.run_approved or not F.get('allow_live_model_calls'):
        raise PermissionError('Live collection is disabled')
    require_freeze()
    if not args.session.isalnum() or len(args.session) > 40:
        raise ValueError('Use a simple alphanumeric session identifier')
    session = CACHE/'private'/args.session
    session.mkdir(parents=True, exist_ok=True, mode=0o700)
    rows = run_phase(args.arm, args.endpoint, session, args.soft_stop_epoch)
    print('F2 phase complete', args.arm, sum(r['status'] == 'solved' for r in rows), 'solved of', len(rows), flush=True)


if __name__ == '__main__':
    main()
