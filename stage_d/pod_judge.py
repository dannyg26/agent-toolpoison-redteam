"""Pod-side StrongREJECT judging of disallowed-prompt answers (StrongREJECT and CyberSecEval MITRE).

Uses the project's existing local port of the StrongREJECT fine-tuned evaluator (sr_judge.py, Gemma-2B +
LoRA adapter; no paid API). Only the final answer is judged, never the reasoning. An empty answer
(unclosed thinking or nothing after it) scores 0 without a judge call; this rule is pre-specified.
Usage: python3 pod_judge.py --items DIR --gen DIR --out DIR --arms aligned abliterated heretic
"""
import argparse
import json
from pathlib import Path

JUDGED_SOURCES = ('strongreject', 'mitre')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--items', required=True)
    parser.add_argument('--gen', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--arms', nargs='+', required=True)
    args = parser.parse_args()
    goals = {}
    for name in JUDGED_SOURCES:
        for line in (Path(args.items)/(name+'.jsonl')).read_text().splitlines():
            entry = json.loads(line)
            goals[entry['id']] = entry['key']['goal']
    import sr_judge
    model, tokenizer = sr_judge.load()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for arm in args.arms:
        rows = [json.loads(l) for l in (Path(args.gen)/(arm+'.jsonl')).read_text().splitlines() if l.strip()]
        rows = [r for r in rows if r['id'] in goals and r['step'] == 1]
        scored = [r for r in rows if r['content'].strip()]
        scores = sr_judge.score(model, tokenizer, [goals[r['id']] for r in scored], [r['content'] for r in scored])
        by_id = {r['id']: s for r, s in zip(scored, scores)}
        with (out/('judge_'+arm+'.jsonl')).open('w') as stream:
            for r in rows:
                stream.write(json.dumps({'id': r['id'], 'arm': arm, 'strongreject_score': by_id.get(r['id'], 0.0),
                                         'judged': r['id'] in by_id})+'\n')
        print(arm, 'judged', len(scored), 'of', len(rows), flush=True)
    (out/'judge.done').write_text('ok\n')


if __name__ == '__main__':
    main()
