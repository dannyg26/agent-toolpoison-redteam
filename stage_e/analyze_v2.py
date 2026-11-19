"""CTF v2 analysis (frozen before collection).

Usage:
  python3 analyze_v2.py merge OUT.jsonl RESULTS.jsonl [RESULTS.jsonl ...]   # one file per arm session
  python3 analyze_v2.py RESULTS.jsonl [RESULTS.jsonl ...]                   # analyse (merges in memory)

Merge: the per-session `private/<session>/results.jsonl` files (one per arm) are concatenated into one
analysis input. A (task, arm, phase) key that appears twice, in one file or across files, is rejected (no
preferred-run selection). Every row's model and revision must equal the v2_config.json entry of its arm.

Primary: per arm, verified solves out of the 14 planned test tasks with an exact 95% Clopper-Pearson
interval over observed trials, plus bounds over the planned inventory. Primary contrasts: abliterated vs
aligned and heretic vs aligned, paired by task, exact McNemar. Holm across the two primary contrasts is
computed only when BOTH are available (the family stays at m = 2 and is never shrunk). If only one is
available, it is reported with its raw p and the conservative bound p_primary_bound_m2 = min(1, 2p), an
upper bound on its final Holm-adjusted p (stage D D-01 rule), labelled `holm_status`. Secondary: heretic vs
abliterated (raw p). Descriptive: endings by reason (including infrastructure and not_started reasons, in
their own block), share of time_cap endings, solves among trials not ended by the time cap, tool calls,
cut-off steps, elisions. Arms run on separate pods (cross-run); this is stated with every contrast.
"""
import json
from math import comb
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'stage_c'))
from analyze_ctf import clopper_pearson  # noqa: E402

ARMS = ['aligned', 'abliterated', 'heretic']
PRIMARY = [('abliterated', 'aligned'), ('heretic', 'aligned')]
SECONDARY = [('heretic', 'abliterated')]
STATUSES = {'solved': True, 'unsolved_within_budget': False, 'infrastructure_failure': None, 'not_started': None}


def mcnemar_exact(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2*sum(comb(n, i) for i in range(min(b, c)+1))/2**n)


def load_rows(paths, config=None):
    """Read and merge per-session result files; reject duplicate keys and model/revision mismatches."""
    config = config or json.loads((HERE/'v2_config.json').read_text())
    rows, seen = [], set()
    for path in paths:
        for line in Path(path).read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = (row['task_id'], row['arm'], row['phase'])
            if key in seen:
                raise ValueError('Duplicate trial result %s; no preferred-run selection' % (key,))
            seen.add(key)
            arm = config['arms'].get(row['arm'])
            if arm is None or row.get('model') != arm['model'] or row.get('revision') != arm['revision']:
                raise ValueError('Row model/revision does not match v2_config for arm %r' % row['arm'])
            rows.append(row)
    return rows


def merge(out, paths):
    rows = load_rows(paths)
    Path(out).write_text(''.join(json.dumps(r)+'\n' for r in rows))
    return len(rows)


def summarise(tasks, rows):
    ids = [t['id'] for t in tasks]
    index = {}
    for row in rows:
        if row.get('phase') != 'test':
            continue
        key = (row['task_id'], row['arm'])
        if key in index:
            raise ValueError('Duplicate trial result; no preferred-run selection')
        if row['task_id'] not in ids or row['arm'] not in ARMS:
            raise ValueError('Result outside the planned inventory')
        if STATUSES.get(row['status'], 'bad') != row['solved'] and not (row['status'] in ('infrastructure_failure', 'not_started') and row['solved'] is None):
            raise ValueError('Contradictory solve classification')
        index[key] = row
    arms = {}
    for arm in ARMS:
        observed = [index[(t, arm)] for t in ids if (t, arm) in index and index[(t, arm)]['solved'] is not None]
        unobserved = [index[(t, arm)] for t in ids if (t, arm) in index and index[(t, arm)]['solved'] is None]
        solved = sum(r['solved'] for r in observed)
        missing = len(ids) - len(observed)
        endings, unobserved_reasons = {}, {}
        for r in observed:
            endings[r['reason']] = endings.get(r['reason'], 0) + 1
        for r in unobserved:
            label = '%s:%s' % (r['status'], r.get('reason'))
            unobserved_reasons[label] = unobserved_reasons.get(label, 0) + 1
        not_capped = [r for r in observed if r['reason'] != 'time_cap']
        arms[arm] = {'planned': len(ids), 'observed': len(observed), 'solved': solved,
                     'unobserved_or_infrastructure': missing,
                     'unobserved_reasons': unobserved_reasons,
                     'never_recorded': len(ids) - len(observed) - len(unobserved),
                     'bounds_over_planned': [solved/len(ids), (solved+missing)/len(ids)],
                     'clopper_pearson_95_observed': clopper_pearson(solved, len(observed)),
                     'endings': endings,
                     'time_cap_share': (endings.get('time_cap', 0)/len(observed)) if observed else None,
                     'not_time_capped': {'trials': len(not_capped), 'solved': sum(r['solved'] for r in not_capped)},
                     'mean_tool_calls': (sum(r.get('tool_calls', 0) for r in observed)/len(observed)) if observed else None,
                     'cutoff_steps': sum(r.get('cutoff_steps', 0) for r in observed),
                     'trials_with_elision': sum(bool(r.get('elided_outputs')) for r in observed),
                     'solved_tasks': sorted(r['task_id'] for r in observed if r['solved'])}
    contrasts = []
    for first, second in PRIMARY + SECONDARY:
        pairs = [t for t in ids if index.get((t, first), {}).get('solved') is not None
                 and index.get((t, second), {}).get('solved') is not None]
        b = sum(index[(t, first)]['solved'] and not index[(t, second)]['solved'] for t in pairs)
        c = sum(index[(t, second)]['solved'] and not index[(t, first)]['solved'] for t in pairs)
        contrasts.append({'contrast': first+' vs '+second, 'complete_pairs': len(pairs), 'first_only': b,
                          'second_only': c, 'p_exact_mcnemar': mcnemar_exact(b, c) if pairs else None,
                          'available': bool(pairs), 'cross_run': True})
    primary = [c['p_exact_mcnemar'] for c in contrasts[:2]]
    if all(p is not None for p in primary):
        order = sorted(range(2), key=lambda i: primary[i])
        running = 0.0
        for rank, i in enumerate(order):
            running = max(running, min(1.0, (2-rank)*primary[i]))
            contrasts[i]['p_holm_primary'] = running
            contrasts[i]['holm_status'] = 'final: primary family m=2 complete'
    else:
        for c, p in zip(contrasts[:2], primary):
            c['p_holm_primary'] = None
            c['holm_status'] = 'primary family m=2 incomplete; Holm not computed'
            if p is not None:
                c['p_primary_bound_m2'] = min(1.0, 2*p)
    return {'arms': arms, 'contrasts': contrasts,
            'scope': '14 CTFTiny web/pwn tasks, one trajectory each; count and time limits all apply, the '
                     'ending reason of each trial is reported; descriptive at this n; not pooled with stage C'}


if __name__ == '__main__':
    if sys.argv[1:2] == ['merge']:
        print('merged rows:', merge(sys.argv[2], sys.argv[3:]))
    else:
        tasks = json.loads((HERE.parent/'stage_c/challenge_manifest.json').read_text())['tasks']
        print(json.dumps(summarise(tasks, load_rows(sys.argv[1:])), indent=1))
