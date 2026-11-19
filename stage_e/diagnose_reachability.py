"""Diagnose intermittent first-connection reachability (R2-01). No model; no flag is printed.

Usage (WSL, root): python3 diagnose_reachability.py ROUNDS TASK [TASK ...]
For every sandbox start: time from `compose start` to the base `wait_healthy()` pass, then 6 probes 3 s
apart, each recording how the probe failed: `getent hosts` (name resolution), `nc -vz -w 3` exit code and
its stderr text, the `docker exec` wall time, and a python create_connection probe. Writes one JSON line per
sandbox to /home/capstone-study/stage_e/reachability_diagnosis.jsonl.
"""
import json
from pathlib import Path
import sys
import time

from environment_v2 import EnvironmentV2

OUT = Path('/home/capstone-study/stage_e/reachability_diagnosis.jsonl')


def probe(env, box, port):
    started = time.monotonic()
    dns = env.exec(['bash', '-c', 'getent hosts %s || echo NO_DNS' % box], timeout=10)
    nc = env.exec(['bash', '-c', 'nc -vz -w 3 %s %s 2>&1; echo "exit=$?"' % (box, port)], timeout=10)
    py = env.exec(['python3', '-c', 'import socket; socket.create_connection((%r, %d), timeout=3).close(); '
                   'print("PY_OPEN")' % (box, int(port))], timeout=10)
    return {'dns': dns['output'].strip()[-80:], 'nc': nc['output'].strip()[-160:],
            'nc_exec_timed_out': nc['timed_out'], 'py_open': 'PY_OPEN' in py['output'],
            'py_tail': py['output'].strip()[-120:], 'probe_seconds': round(time.monotonic()-started, 2)}


def main():
    rounds = int(sys.argv[1])
    for round_number in range(rounds):
        for task_id in sys.argv[2:]:
            t0 = time.monotonic()
            with EnvironmentV2(task_id) as env:
                started = time.monotonic()
                env.wait_healthy()
                healthy = time.monotonic()
                box, port = env.metadata['box'], env.metadata['internal_port']
                probes = []
                for _ in range(6):
                    probes.append(dict(probe(env, box, port), since_healthy=round(time.monotonic()-healthy, 2)))
                    time.sleep(3)
            row = {'round': round_number, 'task_id': task_id, 'start_seconds': round(started-t0, 2),
                   'healthy_seconds': round(healthy-started, 2), 'probes': probes}
            with OUT.open('a') as stream:
                stream.write(json.dumps(row)+'\n')
            summary = ['%s/%s' % ('ok' if 'succeeded' in p['nc'] or 'open' in p['nc'] else 'FAIL',
                                  'ok' if p['py_open'] else 'FAIL') for p in probes]
            print(round_number, task_id, 'healthy %.1fs' % row['healthy_seconds'], summary, flush=True)


if __name__ == '__main__':
    main()
