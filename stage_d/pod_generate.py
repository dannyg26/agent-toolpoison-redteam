"""Pod-side batch generation for one arm (one process per arm so GPU memory is fully released).

Usage on the pod:  python3 pod_generate.py --arm aligned --items DIR --injec DIR --out DIR
Writes OUT/<arm>.jsonl (one row per generated request) and OUT/<arm>.done when complete.
No network calls besides the model download vLLM performs from the pinned revision.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

from injecagent_port import step_one, step_two_case

HERE = Path(__file__).resolve().parent


def split_thinking(text):
    """Qwen3 thinking output: '<reasoning></think><answer>'. Unclosed thinking means no answer."""
    if '</think>' in text:
        reasoning, answer = text.split('</think>', 1)
        return reasoning.replace('<think>', '').strip(), answer.strip(), True
    return text.replace('<think>', '').strip(), '', False


def request_rows(items, config):
    rows = []
    for entry in items:
        rows.append({'id': entry['id'], 'step': 1, 'messages': entry['messages'], 'seed': entry['seed'],
                     'max_tokens': config['max_tokens'][entry['max_tokens_kind']]})
    return rows


def run_batch(llm, rows, config, sampling_class):
    params = [sampling_class(temperature=config['sampling']['temperature'], top_p=config['sampling']['top_p'],
                             top_k=config['sampling']['top_k'], max_tokens=row['max_tokens'], seed=row['seed'])
              for row in rows]
    started = time.time()
    outputs = llm.chat([row['messages'] for row in rows], params, use_tqdm=False,
                       chat_template_kwargs={'enable_thinking': config['enable_thinking']})
    elapsed = time.time() - started
    results = []
    for row, output in zip(rows, outputs):
        completion = output.outputs[0]
        reasoning, answer, closed = split_thinking(completion.text)
        results.append({'id': row['id'], 'step': row['step'], 'content': answer, 'thinking_closed': closed,
                        'reasoning_chars': len(reasoning), 'completion_tokens': len(completion.token_ids),
                        'finish_reason': completion.finish_reason, 'max_tokens': row['max_tokens'],
                        'prompt_sha256': hashlib.sha256(json.dumps(row['messages']).encode()).hexdigest()})
    return results, elapsed


def injecagent_step_two_rows(items, step_one_results, prompts, tools, simulated, config):
    from build_items import injecagent_messages
    by_id = {entry['id']: entry for entry in items}
    rows, unobserved = [], []
    for result in step_one_results:
        entry = by_id.get(result['id'])
        if entry is None or entry['source'].split('_')[0] != 'injecagent' or entry['key']['attack'] != 'ds':
            continue
        parsed = step_one(entry['key']['case'], result['content'])
        if parsed['eval'] != 'succ':
            continue
        case = step_two_case(entry['key']['case'], parsed, simulated)
        if case is None:
            unobserved.append(entry['id'])
            continue
        rows.append({'id': entry['id'], 'step': 2, 'seed': entry['seed'] ^ 0x5A5A5A5A,
                     'max_tokens': config['max_tokens']['agent'],
                     'messages': injecagent_messages(case, prompts[0], prompts[1], tools, step_2=True)})
    return rows, unobserved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--arm', required=True)
    parser.add_argument('--items', required=True)
    parser.add_argument('--injec', required=True, help='dir with prompts.json, tools.json, simulated.json')
    parser.add_argument('--out', required=True)
    parser.add_argument('--tokenizer-from-base', action='store_true',
                        help='pre-registered fallback: load tokenizer/processor files from the aligned base revision')
    args = parser.parse_args()
    config = json.loads((HERE/'run1_config.json').read_text())
    arm = config['arms'][args.arm]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if (out/(args.arm+'.done')).exists():
        raise SystemExit('Arm already complete; no silent regeneration')
    items = []
    for path in sorted(Path(args.items).glob('*.jsonl')):
        items += [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    from vllm import LLM, SamplingParams
    extra = {}
    if args.tokenizer_from_base:
        base = config['arms']['aligned']
        extra = {'tokenizer': base['model'], 'tokenizer_revision': base['revision']}
    # Text-only study: image/video inputs disabled identically for every arm.
    llm = LLM(model=arm['model'], revision=arm['revision'], quantization=config['quantization'],
              max_model_len=config['context_length'], gpu_memory_utilization=0.90, seed=20261119,
              enable_prefix_caching=True, limit_mm_per_prompt={'image': 0, 'video': 0}, **extra)
    log = {'arm': args.arm, 'model': arm['model'], 'revision': arm['revision'], 'items': len(items),
           'tokenizer_from_base': args.tokenizer_from_base}
    results, log['step1_seconds'] = run_batch(llm, request_rows(items, config), config, SamplingParams)
    injec = Path(args.injec)
    prompts = json.loads((injec/'prompts.json').read_text())
    tools = json.loads((injec/'tools.json').read_text())
    simulated = json.loads((injec/'simulated.json').read_text())
    rows, unobserved = injecagent_step_two_rows(items, results, (prompts['system'], prompts['user']),
                                                tools, simulated, config)
    log['step2_requests'], log['step2_unobserved'] = len(rows), len(unobserved)
    if rows:
        step_two, log['step2_seconds'] = run_batch(llm, rows, config, SamplingParams)
        results += step_two
    with (out/(args.arm+'.jsonl')).open('w') as stream:
        for row in results:
            stream.write(json.dumps(dict(row, arm=args.arm))+'\n')
    log['step2_unobserved_ids'] = unobserved
    (out/(args.arm+'.log.json')).write_text(json.dumps(log, indent=1)+'\n')
    (out/(args.arm+'.done')).write_text('ok\n')
    print(json.dumps({k: v for k, v in log.items() if k != 'step2_unobserved_ids'}), flush=True)


if __name__ == '__main__':
    main()
