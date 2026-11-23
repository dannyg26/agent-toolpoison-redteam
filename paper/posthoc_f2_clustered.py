"""Post hoc task-clustered test for F2 solves (review cycle 8, supervisor feedback point 2). Counts only.

    python paper/posthoc_f2_clustered.py > paper/f2_solve_clustered.json

The frozen analysis ran the task-clustered exact sign-flip test for refusal only. The 14 F2 trials per arm
are 7 tasks x 2 trajectories and are not independent, so this applies the same frozen test
(`stage_f/analyze_f.sign_flip_exact`, imported unchanged) to the per-task solve proportions in the released
`stage_f/results/f_derived_aggregates.json` (f2_trials.*.solved_per_task). It also recomputes the frozen
refusal result from `f2_summary.json` per_task as a check.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'stage_f'))
import analyze_f as A  # noqa: E402

agg = json.loads((ROOT/'stage_f/results/f_derived_aggregates.json').read_text(encoding='utf-8'))['f2_trials']
summary = json.loads((ROOT/'stage_f/results/f2_summary.json').read_text(encoding='utf-8'))
tasks = sorted(summary['per_task'])
solve = {arm: {t: agg[arm]['solved_per_task'].get(t, 0)/2 for t in tasks} for arm in A.ARMS}
refuse = {arm: {t: int(summary['per_task'][t][arm].split('/')[0])/2 for t in tasks} for arm in A.ARMS}

out = {'_about': 'Post hoc (review cycle 8). Exact paired sign-flip permutation test over the 7 F2 tasks '
                 '(frozen analyze_f.sign_flip_exact) on per-task solve proportions; refusal recomputed as a '
                 'check against the frozen f2_summary.json. Raw p, two-sided. Counts only.',
       'tasks': len(tasks), 'contrasts': []}
for first, second in A.PRIMARY + A.SECONDARY:
    row = {'contrast': first+' vs '+second}
    for name, table in (('solved', solve), ('refused_check', refuse)):
        diffs = [table[first][t] - table[second][t] for t in tasks]
        row[name] = {'tasks_with_difference': sum(d != 0 for d in diffs),
                     'mean_task_difference': round(sum(diffs)/len(diffs), 4),
                     'p_sign_flip': A.sign_flip_exact(diffs)}
    out['contrasts'].append(row)
print(json.dumps(out, indent=2))
