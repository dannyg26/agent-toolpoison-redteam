"""Pinned inference command. Default is dry-run; never rents a GPU or installs packages."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

from guard_adapter import guard, verify_ready
from freeze_tools import source_hash

HERE = Path(__file__).resolve().parent


def serving_command(config, condition):
    prefix = 'main' if condition == 'main' else 'control'
    return [sys.executable, '-m', 'vllm.entrypoints.openai.api_server',
            '--model', config[prefix+'_model'], '--revision', config[prefix+'_revision'],
            '--served-model-name', 'csc-'+condition, '--quantization', config['quantization'],
            '--max-model-len', str(config['context_length']), '--max-num-seqs', '1',
            '--gpu-memory-utilization', '0.90', '--enable-auto-tool-choice',
            '--tool-call-parser', 'qwen3_coder', '--reasoning-parser', 'qwen3',
            '--host', '127.0.0.1', '--port', '8000', '--seed', '20261118']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--condition', choices=['main', 'control'], required=True)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--guard-ready')
    parser.add_argument('--key-file')
    parser.add_argument('--verified-all-in-hourly', type=float)
    args = parser.parse_args()
    config_path = HERE/'study_config.json'
    config = json.loads(config_path.read_text())
    argv = serving_command(config, args.condition)
    if not args.run:
        print(json.dumps({'dry_run': True, 'gpu_rented': False, 'model_calls': 0,
                          'required_vllm_version': '0.33.0', 'command': argv}, indent=2))
        return
    if not config.get('allow_live_model_calls', False):
        raise PermissionError('Live model setup is disabled pending review and freeze')
    if not all((args.guard_ready, args.key_file, args.verified_all_in_hourly)):
        raise PermissionError('Verified live pod guard, private key path and actual quote required')
    snapshot = json.loads((HERE/'ctf_freeze.json').read_text())
    if (not snapshot.get('externally_timestamped_before_collection') or
            snapshot['sha256'].get('study_config.json') != source_hash(config_path)):
        raise PermissionError('Frozen model configuration not verified')
    ready = json.loads(Path(args.guard_ready).read_text())
    if ready.get('pod_id') != os.environ.get('RUNPOD_POD_ID'):
        raise PermissionError('This is not the guarded pod')
    os.kill(int(ready['guard_pid']), 0)
    keypath = Path(args.key_file)
    if keypath.stat().st_mode & 0o077:
        raise PermissionError('Key file must have mode 600')
    pod = guard.api_request('GET', ready['pod_id'], keypath.read_text().strip())
    stop = verify_ready(ready, pod, config, time.time(), args.verified_all_in_hourly)
    if stop-time.time() < 600:
        raise TimeoutError('Insufficient guarded session time for a model load')
    version = importlib.metadata.version('vllm')
    if version != '0.33.0':
        raise RuntimeError('Install the pinned vLLM version before proceeding')
    metadata = {'condition': args.condition, 'vllm': version, 'argv': argv,
                'config_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest(),
                'pod_id': ready['pod_id'], 'verified_deadline': stop}
    out = Path(args.guard_ready).parent
    (out/('inference-'+args.condition+'-metadata.json')).write_text(json.dumps(metadata, indent=2)+'\n')
    os.execv(sys.executable, argv)


if __name__ == '__main__':
    main()
