"""F1 pod-side work for one arm (one process per step so GPU memory is released between steps).

  python3 pod_f1.py generate --arm ARM   # offline vLLM batch over items_f1.jsonl -> OUT/ARM.jsonl + ARM.done
  python3 pod_f1.py judge --arm ARM      # StrongREJECT judge on ARM's answers -> OUT/judge_ARM.jsonl + .done

Primary answer rule (pre-registered, unchanged): the answer is the text after the first literal `</think>`
in the generated text; no `</think>` means unclosed thinking and an empty answer, which scores 0 without a
judge call.

Fallback rule (pre-registered; used ONLY in the sensitivity analysis that runs when any arm's
closed-thinking rate is below 50%, R5-07), applied per completion:
  (i)  if the primary rule found `</think>`, the fallback answer equals the primary answer;
  (ii) else, if the tokenizer's `</think>` token id occurs in the generated token ids (the marker was
       dropped from the text as a special token), the answer is the decoded text (skip_special_tokens=True)
       of the tokens after its first occurrence;
  (iii) else, if the text contains neither `<think>` nor `</think>` and finish_reason is 'stop' (no think
       markup at all, e.g. a template that ignores enable_thinking), the whole text is the answer
       (`no_think_markup`);
  (iv) otherwise the fallback answer is empty.

Files per arm, each with a `.done` marker holding the file's SHA-256 (the launcher checks it on fetch):
  ARM_raw.jsonl            raw generated text + finish reason + think-end token index (private audit)
  provenance_ARM.jsonl     tokenizer/template/generation-config hashes, think-end token id, and the
                           rendered token count + hash of one fixed benign probe prompt (D-28 visibility)
  thinking_check_ARM.jsonl closed-thinking count and rate; alert=true if the rate is below 0.5 (recorded,
                           never aborts)
  ARM.jsonl                primary answer (`content`) and `fallback_content` per prompt (written last)
  judge_ARM.jsonl          StrongREJECT score of the primary answer and of the fallback answer
"""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = Path('/root/out/f1')
CONFIG = json.loads((HERE/'f_config.json').read_text())
_V2_PATH = HERE/'v2_config.json'                        # shipped next to this file on the pod
V2 = json.loads((_V2_PATH if _V2_PATH.exists() else HERE.parent/'stage_e/v2_config.json').read_text())
THINK_END = '</think>'
CLOSED_RATE_ALERT = 0.5
BENIGN_PROBE = 'What is the capital of France?'


def split_thinking(text):
    if THINK_END in text:
        reasoning, answer = text.split(THINK_END, 1)
        return reasoning.replace('<think>', '').strip(), answer.strip(), True
    return text.replace('<think>', '').strip(), '', False


def fallback_answer(text, token_ids, think_end_id, decode, finish_reason):
    """Return (answer, path) under the pre-registered fallback rule; path names the branch used."""
    _, answer, closed = split_thinking(text)
    if closed:
        return answer, 'closed'
    if think_end_id is not None and think_end_id in token_ids:
        index = list(token_ids).index(think_end_id)
        return decode(list(token_ids)[index+1:]).strip(), 'think_end_token'
    if '<think>' not in text and THINK_END not in text and finish_reason == 'stop':
        return text.strip(), 'no_think_markup'
    return '', 'none'


def thinking_check(arm, rows):
    n = len(rows)
    closed = sum(r['thinking_closed'] for r in rows)
    paths = [r['fallback_path'] for r in rows]
    return {'arm': arm, 'n': n, 'thinking_closed': closed, 'closed_rate': closed/n if n else 0.0,
            'alert': (closed/n if n else 0.0) < CLOSED_RATE_ALERT,
            'fallback_paths': {p: paths.count(p) for p in ('closed', 'think_end_token', 'no_think_markup', 'none')}}


def write_with_marker(stem, lines):
    """Write OUT/stem.jsonl, then OUT/stem.done holding its SHA-256."""
    path = OUT/(stem+'.jsonl')
    with path.open('w') as stream:
        for line in lines:
            stream.write(json.dumps(line)+'\n')
    (OUT/(stem+'.done')).write_text(hashlib.sha256(path.read_bytes()).hexdigest()+'\n')


def items():
    return [json.loads(l) for l in (HERE/'items_f1.jsonl').read_text().splitlines() if l.strip()]


def provenance(arm, spec, tokenizer, think_end_id):
    record = {'arm': arm, 'model': spec['model'], 'revision': spec['revision'], 'think_end_token_id': think_end_id}
    try:
        from huggingface_hub import snapshot_download
        import vllm
        record['vllm'] = vllm.__version__
        path = Path(snapshot_download(spec['model'], revision=spec['revision'], local_files_only=True))
        record['sha256'] = {n: hashlib.sha256((path/n).read_bytes()).hexdigest()
                            for n in ('tokenizer_config.json', 'chat_template.jinja', 'tokenizer.json',
                                      'generation_config.json') if (path/n).is_file()}
    except Exception as error:                      # provenance is diagnostic; never blocks generation
        record['sha256_error'] = type(error).__name__
    try:
        rendered = tokenizer.apply_chat_template([{'role': 'user', 'content': BENIGN_PROBE}], tokenize=False,
                                                 add_generation_prompt=True,
                                                 enable_thinking=CONFIG['f1']['enable_thinking'])
        ids = tokenizer(rendered, add_special_tokens=False)['input_ids']
        record['benign_probe'] = {'prompt': BENIGN_PROBE, 'rendered_sha256': hashlib.sha256(rendered.encode()).hexdigest(),
                                  'token_count': len(ids), 'rendered_ends_with_think_open': rendered.rstrip().endswith('<think>')}
    except Exception as error:
        record['benign_probe_error'] = type(error).__name__
    return record


def generate(arm):
    from vllm import LLM, SamplingParams
    spec = V2['arms'][arm]
    llm = LLM(model=spec['model'], revision=spec['revision'], quantization=V2['quantization'],
              max_model_len=V2['context_length'], gpu_memory_utilization=0.90, seed=20261120,
              enable_prefix_caching=True, limit_mm_per_prompt={'image': 0, 'video': 0})
    tokenizer = llm.get_tokenizer()
    think_end_id = tokenizer.convert_tokens_to_ids(THINK_END)
    if not isinstance(think_end_id, int) or think_end_id == getattr(tokenizer, 'unk_token_id', None):
        think_end_id = None
    def decode(ids):
        return tokenizer.decode(ids, skip_special_tokens=True)
    rows = items()
    params = [SamplingParams(temperature=V2['temperature'], top_p=V2['top_p'], top_k=V2['top_k'],
                             max_tokens=CONFIG['f1']['max_tokens'], seed=r['seed']) for r in rows]
    outputs = llm.chat([[{'role': 'user', 'content': r['prompt']}] for r in rows], params, use_tqdm=False,
                       chat_template_kwargs={'enable_thinking': CONFIG['f1']['enable_thinking']})
    OUT.mkdir(parents=True, exist_ok=True)
    answers, raw = [], []
    for row, output in zip(rows, outputs):
        completion = output.outputs[0]
        token_ids = list(completion.token_ids)
        reasoning, answer, closed = split_thinking(completion.text)
        fallback, path = fallback_answer(completion.text, token_ids, think_end_id, decode, completion.finish_reason)
        answers.append({'id': row['id'], 'arm': arm, 'content': answer, 'thinking_closed': closed,
                        'fallback_content': fallback, 'fallback_path': path,
                        'reasoning_chars': len(reasoning), 'completion_tokens': len(token_ids),
                        'finish_reason': completion.finish_reason})
        raw.append({'id': row['id'], 'arm': arm, 'text': completion.text, 'finish_reason': completion.finish_reason,
                    'think_end_token_index': (token_ids.index(think_end_id)
                                              if think_end_id is not None and think_end_id in token_ids else None)})
    write_with_marker(arm+'_raw', raw)
    write_with_marker('provenance_'+arm, [provenance(arm, spec, tokenizer, think_end_id)])
    check = thinking_check(arm, answers)
    write_with_marker('thinking_check_'+arm, [check])
    print('THINKING_CHECK', json.dumps(check), flush=True)
    write_with_marker(arm, answers)                 # ARM.done last: generation is complete


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
    # Primary answers, plus fallback answers that differ from them (only for the sensitivity analysis).
    jobs = [(a['id'], 'primary', a['content']) for a in answers if a['content'].strip()]
    jobs += [(a['id'], 'fallback', a['fallback_content']) for a in answers
             if a.get('fallback_content', '').strip() and a['fallback_content'] != a['content']]
    scores = sr_judge.score(model, tokenizer, [goals[i] for i, _, _ in jobs], [t for _, _, t in jobs]) if jobs else []
    by_key = {(i, kind): s for (i, kind, _), s in zip(jobs, scores)}
    lines = []
    for a in answers:
        primary = by_key.get((a['id'], 'primary'), 0.0)
        fallback = by_key.get((a['id'], 'fallback'), primary if a.get('fallback_content', '') == a['content'] else 0.0)
        lines.append({'id': a['id'], 'arm': arm, 'strongreject_score': primary, 'judged': (a['id'], 'primary') in by_key,
                      'fallback_strongreject_score': fallback})
    write_with_marker('judge_'+arm, lines)


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
