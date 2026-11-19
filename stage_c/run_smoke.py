"""Approved model compatibility checks on development tasks; no cloud rental."""
import argparse
import hashlib
import json
import os
import time

from endpoint_client import EndpointClient
from environment import CACHE, HERE, Environment
from run_phase import require_freeze
from trajectory import ExactGrader, run_trajectory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--condition', required=True, choices=['main', 'control'])
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--session', required=True)
    parser.add_argument('--soft-stop-epoch', required=True, type=float)
    parser.add_argument('--run-approved', action='store_true')
    args = parser.parse_args()
    config = json.loads((HERE/'study_config.json').read_text())
    if not args.run_approved or not config.get('allow_live_model_calls', False):
        raise PermissionError('Live model calls disabled')
    require_freeze()
    if not args.session.isalnum() or len(args.session) > 40:
        raise ValueError('Invalid session identifier')
    session = CACHE/'private'/args.session
    session.mkdir(parents=True, exist_ok=True, mode=0o700)
    config['task_seconds'] = config['development_task_seconds']
    for task in json.loads((HERE/'development_manifest.json').read_text())['tasks']:
        if time.time()+config['task_seconds']+60 >= args.soft_stop_epoch:
            raise TimeoutError('Insufficient session time for development check')
        config['seed'] = int(hashlib.sha256(task['id'].encode()).hexdigest()[:8], 16)
        result_path = session/(task['id']+'-'+args.condition+'-development.json')
        if result_path.exists():
            raise ValueError('Development trial already recorded; do not silently retry')
        client = EndpointClient(args.endpoint, 'csc-'+args.condition, config, approved=True)
        with Environment(task['id'], discovery=True) as environment:
            environment.wait_healthy()
            class Values(dict):
                def __missing__(self, key):
                    return '{'+key+'}'
            meta = environment.metadata
            description = meta['description'].format_map(Values(box=meta['box'], port=meta['internal_port']))
            trace = session/(task['id']+'-'+args.condition+'-development-trace.jsonl')
            def record(event):
                with trace.open('a') as stream:
                    stream.write(json.dumps(event)+'\n')
                    stream.flush()
                    os.fsync(stream.fileno())
            result = run_trajectory(client, environment, ExactGrader(meta['flag']), description,
                                    config, record=record)
        result_path.write_text(json.dumps(result, indent=2)+'\n')
        # Solving is not required for a parser/terminal compatibility check.
        if result['status'] == 'infrastructure_failure' or result['successful_terminal_calls'] == 0:
            raise RuntimeError('Development interface check failed; no held-out collection may start')
        print('Model interface compatible', task['id'], args.condition, flush=True)


if __name__ == '__main__':
    main()
