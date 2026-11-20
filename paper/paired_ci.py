"""Post hoc paired-difference confidence intervals for the CTF v2 contrasts (paper, repair cycle 4).

POST HOC / DESCRIPTIVE. Not part of the frozen analyze_v2.py. Reads only the released summary JSONs
(no traces, no flags) and writes paper/figures/paired_ci.json.

    python paper/paired_ci.py

Methods (both for the paired difference d = p_first - p_second over the same 14 tasks):
- Tango (1998) score 95% interval, imported unchanged from stage_b/analyze_heldout.py (the method the
  stage B held-out study pre-registered and stage D D-14 prescribes).
- Newcombe (1998) hybrid score interval for paired data ("method 10"): Wilson intervals for each marginal
  proportion combined with the phi correlation; when ad > bc, ad - bc is replaced by max(ad - bc - n/2, 0),
  as Newcombe recommends. Reported as a cross-check.
"""
import json
import sys
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'stage_b'))
from analyze_heldout import tango_ci, wilson, mcnemar_exact, Z  # noqa: E402


def newcombe_paired(a, b, c, d, z=Z):
    """a = both, b = first only, c = second only, d = neither. Returns (lo, hi) for (b - c) / n."""
    n = a + b + c + d
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n, z)
    l2, u2 = wilson(a + c, n, z)
    denom = (a + b) * (c + d) * (a + c) * (b + d)
    num = a * d - b * c
    if num > 0:
        num = max(num - n / 2, 0.0)
    phi = num / sqrt(denom) if denom > 0 else 0.0
    diff = p1 - p2
    lower = diff - sqrt(max((p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2, 0.0))
    upper = diff + sqrt(max((u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2, 0.0))
    return max(-1.0, lower), min(1.0, upper)


def main():
    summary = json.loads((ROOT / 'stage_e/results/ctf_v2_summary.json').read_text(encoding='utf-8'))
    posthoc = json.loads((ROOT / 'stage_e/results/posthoc_v2.json').read_text(encoding='utf-8'))
    tasks = sorted(posthoc['tasks'])
    assert len(tasks) == 14, tasks
    solved = {arm: set(v['solved_tasks']) for arm, v in summary['arms'].items()}
    rows = []
    for first, second, role in [('abliterated', 'aligned', 'primary'), ('heretic', 'aligned', 'primary'),
                                ('heretic', 'abliterated', 'secondary')]:
        a = sum(t in solved[first] and t in solved[second] for t in tasks)
        b = sum(t in solved[first] and t not in solved[second] for t in tasks)
        c = sum(t not in solved[first] and t in solved[second] for t in tasks)
        d = len(tasks) - a - b - c
        n = len(tasks)
        t_lo, t_hi = tango_ci(b, c, n)
        n_lo, n_hi = newcombe_paired(a, b, c, d)
        rows.append({'contrast': '%s vs %s' % (first, second), 'role': role, 'n': n, 'both': a,
                     'first_only': b, 'second_only': c, 'neither': d, 'difference': round((b - c) / n, 4),
                     'tango_95ci': [round(t_lo, 4), round(t_hi, 4)],
                     'newcombe10_95ci': [round(n_lo, 4), round(n_hi, 4)],
                     'mcnemar_exact_p': mcnemar_exact(b, c)})
    out = {'label': 'POST HOC / DESCRIPTIVE (paper repair cycle 4). Not produced by the frozen analyze_v2.py.',
           'sources': ['stage_e/results/ctf_v2_summary.json', 'stage_e/results/posthoc_v2.json'],
           'methods': {'tango': 'stage_b/analyze_heldout.py tango_ci (Tango 1998 score interval)',
                       'newcombe10': 'Newcombe 1998 hybrid score interval for paired data, method 10'},
           'contrasts': rows}
    target = ROOT / 'paper/figures/paired_ci.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(rows, indent=1))


if __name__ == '__main__':
    main()
