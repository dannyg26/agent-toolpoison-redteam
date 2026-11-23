"""Post hoc F1 StrongREJECT score sensitivity (review cycle 8, supervisor feedback point 1). Counts and means only.

    python3 paper/posthoc_f1_scores.py SESSION_DIR > paper/f1_score_sensitivity.json

SESSION_DIR is the private F1 session (ARM.jsonl + judge_ARM.jsonl), readable only inside the collection host.
Rows are loaded and classified exactly as the frozen `stage_f/analyze_f.py f1` does (same willingness rule,
same `finish_reason == 'length'` cap flag, same judge field, same bootstrap settings). This script never
writes model text: its output is counts, means, intervals and p-values.

Reported per arm:
  - all 313 prompts (reproduces the frozen mean, as a check);
  - answered prompts only (class != no_answer; an unclosed thinking block gives an empty answer, scored 0);
  - answered and not length-capped;
  - a check that every no_answer prompt received score 0.
Reported per contrast (paired by prompt, Wilcoxon signed-rank as frozen, raw p, no Holm):
  - prompts answered in both arms;
  - prompts answered and not length-capped in both arms (the frozen full-refusal sensitivity set).
"""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'stage_f'))
import analyze_f as A  # noqa: E402  (frozen; imported, not modified)


def load(session):
    session = Path(session)
    ids = [i['id'] for i in A._read_jsonl(Path('/home/capstone-study/stage_f')/'items_f1.jsonl')]
    data = {}
    for arm in A.ARMS:
        rows = {r['id']: r for r in A._read_jsonl(session/(arm+'.jsonl'))}
        scores = {r['id']: r for r in A._read_jsonl(session/('judge_'+arm+'.jsonl'))}
        assert sorted(rows) == sorted(ids) and sorted(scores) == sorted(ids), arm
        data[arm] = {i: {'class': A.classify_willingness(rows[i]['content']),
                         'score': scores[i]['strongreject_score'],
                         'length_capped': rows[i]['finish_reason'] == 'length'} for i in ids}
    return ids, data


def mean_block(values):
    n = len(values)
    if n == 0:
        return {'n': 0, 'mean': None, 'ci95_bootstrap': None}
    return {'n': n, 'mean': round(sum(values)/n, 4),
            'ci95_bootstrap': A.bootstrap_mean_ci(values, A.F['f1']['bootstrap_resamples'], A.F['f1']['bootstrap_seed'])}


def main(session):
    ids, data = load(session)
    answered = lambda r: r['class'] != 'no_answer'                                 # noqa: E731
    clean = lambda r: answered(r) and not r['length_capped']                         # noqa: E731
    out = {'_about': 'Post hoc (review cycle 8). F1 StrongREJECT score among answered prompts. Counts, means, '
                     'percentile-bootstrap 95% CIs (frozen settings) and Wilcoxon p (raw) only; no model text. '
                     'Produced by paper/posthoc_f1_scores.py from the private F1 session.',
           'arms': {}, 'contrasts': []}
    for arm, rows in data.items():
        r = list(rows.values())
        out['arms'][arm] = {
            'all_prompts': mean_block([x['score'] for x in r]),
            'answered': mean_block([x['score'] for x in r if answered(x)]),
            'answered_not_length_capped': mean_block([x['score'] for x in r if clean(x)]),
            'no_answer_count': sum(not answered(x) for x in r),
            'no_answer_with_nonzero_score': sum(not answered(x) and x['score'] != 0 for x in r),
        }
    for first, second in A.PRIMARY + A.SECONDARY:
        entry = {'contrast': first+' vs '+second}
        for name, keep in (('answered_in_both', answered), ('answered_not_capped_in_both', clean)):
            pairs = [i for i in ids if keep(data[first][i]) and keep(data[second][i])]
            diffs = [data[first][i]['score'] - data[second][i]['score'] for i in pairs]
            entry[name] = {'n_pairs': len(pairs),
                           'mean_first': round(sum(data[first][i]['score'] for i in pairs)/len(pairs), 4) if pairs else None,
                           'mean_second': round(sum(data[second][i]['score'] for i in pairs)/len(pairs), 4) if pairs else None,
                           'mean_difference': round(sum(diffs)/len(diffs), 4) if diffs else None,
                           'p_wilcoxon_raw': A.wilcoxon_signed_rank(diffs) if diffs else None}
        out['contrasts'].append(entry)
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main(sys.argv[1])
