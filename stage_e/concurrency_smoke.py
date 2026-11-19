"""Free no-model concurrency smoke test of the v2 sandboxes on this host (R2-11). No model, no flag printed.

Runs test tasks three at a time through a ThreadPoolExecutor, in the fixed run_arm_v2 order (the first
round is exactly the three sandboxes a real arm starts first). Each sandbox does what a trial does before
and around the model: EnvironmentV2 start, wait_healthy(), the reachability gate wait_reachable(), then
a few terminal commands, then teardown. A sampler records `free -m` every 2 s and `docker stats` every
10 s. Writes /home/capstone-study/stage_e/concurrency_smoke.json.
Usage (WSL, root): python3 concurrency_smoke.py [N_TASKS]   (default 3; 14 = full soak of all test tasks)
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

from environment_v2 import EnvironmentV2, TargetUnreachable, agent_v2_image_id

HERE = Path(__file__).resolve().parent
OUT = Path('/home/capstone-study/stage_e/concurrency_smoke.json')
COMMANDS = ['id -u', 'ls -la /work | head -5', 'python3 -c "print(6*7)"', 'xxd -l 16 /bin/ls | head -1']


def memory():
    lines = subprocess.run(['free', '-m'], capture_output=True, text=True).stdout.splitlines()
    mem = lines[1].split()
    swap = lines[2].split()
    return {'total': int(mem[1]), 'used': int(mem[2]), 'available': int(mem[6]), 'swap_used': int(swap[2])}


def docker_stats():
    out = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{.Name}} {{.MemUsage}} {{.CPUPerc}}'],
                         capture_output=True, text=True, timeout=60).stdout
    return [l for l in out.splitlines() if l.startswith('csc-')]


def sandbox(task_id, in_flight, lock, t0):
    row = {'task_id': task_id}
    with lock:
        in_flight[0] += 1
        row['in_flight_at_start'] = in_flight[0]
    started = time.monotonic()
    row['start_offset_seconds'] = round(started - t0, 1)
    try:
        with EnvironmentV2(task_id) as env:
            row['start_seconds'] = round(time.monotonic()-started, 2)
            mark = time.monotonic()
            env.wait_healthy()
            row['healthy_seconds'] = round(time.monotonic()-mark, 2)
            mark = time.monotonic()
            try:
                row['reachability_attempts'] = env.wait_reachable()
                row['reachability_gate'] = True
            except TargetUnreachable as error:
                row['reachability_attempts'], row['reachability_gate'] = error.attempts, False
            row['gate_seconds'] = round(time.monotonic()-mark, 2)
            results = []
            for command in COMMANDS:
                mark = time.monotonic()
                r = env.terminal(command, 30)
                results.append({'command': command, 'exit_code': r['exit_code'], 'timed_out': r['timed_out'],
                                'seconds': round(time.monotonic()-mark, 2),
                                'infrastructure_error': bool(r.get('infrastructure_error'))})
            row['terminal'] = results
            row['terminal_ok'] = all(x['exit_code'] == 0 and not x['timed_out'] for x in results)
            close_mark = time.monotonic()
        row['close_seconds'] = round(time.monotonic()-close_mark, 2)
    except Exception as error:
        row['error'] = '%s: %s' % (type(error).__name__, str(error)[:300])
    finally:
        with lock:
            in_flight[0] -= 1
    row['total_seconds'] = round(time.monotonic()-started, 2)
    print(task_id, {k: row.get(k) for k in ('start_seconds', 'healthy_seconds', 'reachability_attempts',
                                            'gate_seconds', 'terminal_ok', 'close_seconds', 'error')}, flush=True)
    return row


def main():
    sys.path.insert(0, str(HERE))
    import run_arm_v2 as R
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    tasks = [t['id'] for t in R.ordered(json.loads((HERE.parent/'stage_c/challenge_manifest.json').read_text())['tasks'])][:count]
    samples, stats, stop = [], [], threading.Event()
    t0 = time.monotonic()

    def sampler():
        tick = 0
        while not stop.is_set():
            samples.append(dict(memory(), t=round(time.monotonic()-t0, 1)))
            if tick % 5 == 0:
                stats.append({'t': round(time.monotonic()-t0, 1), 'containers': docker_stats()})
            tick += 1
            stop.wait(2)
    baseline = memory()
    thread = threading.Thread(target=sampler, daemon=True)
    thread.start()
    in_flight, lock = [0], threading.Lock()
    with ThreadPoolExecutor(max_workers=R.CONFIG['concurrency']) as pool:
        rows = list(pool.map(lambda t: sandbox(t, in_flight, lock, t0), tasks))
    stop.set()
    thread.join()
    report = {'when': datetime.now(timezone.utc).isoformat(), 'agent_v2_image': agent_v2_image_id(),
              'host': {'cpus': int(subprocess.run(['nproc'], capture_output=True, text=True).stdout),
                       'baseline_memory_mb': baseline},
              'concurrency': R.CONFIG['concurrency'], 'tasks': tasks, 'sandboxes': rows,
              'memory_min_available_mb': min(s['available'] for s in samples),
              'memory_max_used_mb': max(s['used'] for s in samples),
              'swap_max_used_mb': max(s['swap_used'] for s in samples),
              'max_in_flight': max(r.get('in_flight_at_start', 0) for r in rows),
              'memory_samples': samples, 'docker_stats_samples': stats,
              'wall_seconds': round(time.monotonic()-t0, 1)}
    report['all_gates_pass'] = all(r.get('reachability_gate') for r in rows)
    report['all_ok'] = report['all_gates_pass'] and all(r.get('terminal_ok') and 'error' not in r for r in rows)
    OUT.write_text(json.dumps(report, indent=1)+'\n')
    print(json.dumps({k: report[k] for k in ('tasks', 'max_in_flight', 'memory_min_available_mb', 'memory_max_used_mb',
                                             'swap_max_used_mb', 'all_gates_pass', 'all_ok', 'wall_seconds')}))


if __name__ == '__main__':
    main()
