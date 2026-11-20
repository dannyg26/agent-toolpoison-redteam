"""F1 pod-side work for one arm (one process per step so GPU memory is released between steps).

  python3 pod_f1.py generate --arm ARM   # offline vLLM batch over items_f1.jsonl -> OUT/ARM.jsonl + ARM.done
  python3 pod_f1.py judge --arm ARM      # StrongREJECT judge on ARM's answers -> OUT/judge_ARM.jsonl + .done

The answer is the text after </think>; unclosed thinking means an empty answer, which scores 0 without a
judge call. The judge is the project's sr_judge.score with the base model and adapter pinned by revision.
"""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = Path('/root/out/f1')
CONFIG = json.loads((HERE/'f_config.json').read_text())
V2 = json.loads((HERE/'v2_config.json').read_text())


def split_thinking(text):
    if '</think>' in text:
        reasoning, answer = text.split('</think>', 1)
        return reasoning.replace('<think>', '').strip(), answer.strip(), True
    return text.replace('<think>', '').strip(), '', False


def items():
    return [json.loads(l) for l in (HERE/'items_f1.jsonl').read_text().splitlines() if l.strip()]


def generate(arm):
    from vllm import LLM, SamplingParams
    spec = V2['arms'][arm]
    llm = LLM(model=spec['model'], revision=spec['revision'], quantization=V2['quantization'],
              max_model_len=V2['context_length'], gpu_memory_utilization=0.90, seed=20261120,
              enable_prefix_caching=True, limit_mm_per_prompt={'image': 0, 'video': 0})
    rows = items()
    params = [SamplingParams(temperature=V2['temperature'], top_p=V2['top_p'], top_k=V2['top_k'],
                             max_tokens=CONFIG['f1']['max_tokens'], seed=r['seed']) for r in rows]
    outputs = llm.chat([[{'role': 'user', 'content': r['prompt']}] for r in rows], params, use_tqdm=False,
                       chat_template_kwargs={'enable_thinking': CONFIG['f1']['enable_thinking']})
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/(arm+'.jsonl')).open('w') as stream:
        for row, output in zip(rows, outputs):
            completion = output.outputs[0]
            reasoning, answer, closed = split_thinking(completion.text)
            stream.write(json.dumps({'id': row['id'], 'arm': arm, 'content': answer, 'thinking_closed': closed,
                                     'reasoning_chars': len(reasoning), 'completion_tokens': len(completion.token_ids),
                                     'finish_reason': completion.finish_reason})+'\n')
    digest = hashlib.sha256((OUT/(arm+'.jsonl')).read_bytes()).hexdigest()
    (OUT/(arm+'.done')).write_text(digest+'\n')


def judge(arm):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    import sr_judge
    spec = CONFIG['f1']['judge']
    tokenizer = AutoTokenizer.from_pretrained(spec['adapter'], revision=spec['adapter_revision'],
                                              padding_side='left', truncation_side='left')
    if not tokenizer.pad_token:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(spec['base'], revision=spec['base_revision'], device_map='cuda',
                                                 torch_dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(model, spec['adapter'], revision=spec['adapter_revision'])
    model.eval()
    goals = {r['id']: r['prompt'] for r in items()}
    answers = [json.loads(l) for l in (OUT/(arm+'.jsonl')).read_text().splitlines() if l.strip()]
    scored = [a for a in answers if a['content'].strip()]
    scores = sr_judge.score(model, tokenizer, [goals[a['id']] for a in scored], [a['content'] for a in scored])
    by_id = {a['id']: s for a, s in zip(scored, scores)}
    with (OUT/('judge_'+arm+'.jsonl')).open('w') as stream:
        for a in answers:
            stream.write(json.dumps({'id': a['id'], 'arm': arm, 'strongreject_score': by_id.get(a['id'], 0.0),
                                     'judged': a['id'] in by_id})+'\n')
    (OUT/('judge_'+arm+'.done')).write_text('ok\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('step', choices=['generate', 'judge'])
    parser.add_argument('--arm', required=True, choices=sorted(V2['arms']))
    args = parser.parse_args()
    marker = OUT/((args.arm if args.step == 'generate' else 'judge_'+args.arm)+'.done')
    if marker.exists():
        raise SystemExit('Step already complete; no silent regeneration')
    generate(args.arm) if args.step == 'generate' else judge(args.arm)


if __name__ == '__main__':
    main()
