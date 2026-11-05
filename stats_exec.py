"""Bootstrap statistics for the agent benchmark: the SAFEGUARDS contrast on VERIFIED leaks.

Pools all accumulated episode files and reports, with hand-written bootstrap 95% CIs:
  - per (label, reasoning): the executed-exfil rate (a verified leak, not intent);
  - the safeguards effect: ASR(abliterated) - ASR(safeguarded), per reasoning setting;
  - the reasoning effect within each model: ASR(reasoning ON) - ASR(OFF).

Run: python stats_exec.py --glob "results/agent_*.json"
     python stats_exec.py --metric unauthorized_read       # level-1 harm instead of verified leak
"""
from __future__ import annotations
import argparse
import glob
import json
import random
from collections import defaultdict


def boot_ci(vals, iters=10000, alpha=0.05):
    if not vals:
        return (0.0, 0.0, 0.0)
    n = len(vals)
    mean = sum(vals) / n
    means = []
    for _ in range(iters):
        s = sum(vals[random.randrange(n)] for _ in range(n))
        means.append(s / n)
    means.sort()
    return (mean, means[int(alpha / 2 * iters)], means[int((1 - alpha / 2) * iters)])


def boot_diff(a, b, iters=10000, alpha=0.05):
    """CI for mean(a) - mean(b) via independent resampling."""
    if not a or not b:
        return (0.0, 0.0, 0.0)
    na, nb = len(a), len(b)
    da = []
    for _ in range(iters):
        sa = sum(a[random.randrange(na)] for _ in range(na)) / na
        sb = sum(b[random.randrange(nb)] for _ in range(nb)) / nb
        da.append(sa - sb)
    da.sort()
    return (sum(a) / na - sum(b) / nb, da[int(alpha / 2 * iters)], da[int((1 - alpha / 2) * iters)])


def _sig(lo, hi):
    return "SIGNIFICANT (CI excludes 0)" if (lo > 0 or hi < 0) else "not significant (CI includes 0)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="results/agent_*.json")
    ap.add_argument("--metric", default="executed_exfil",
                    choices=["executed_exfil", "unauthorized_read", "benign_completed"])
    ap.add_argument("--safeguarded-label", default="safeguarded")
    ap.add_argument("--abliterated-label", default="abliterated")
    ap.add_argument("--exclude-blatant", action="store_true",
                    help="drop the blatant sanity-floor framing from the pooled rates")
    args = ap.parse_args()

    # metric (1/0) lists keyed by (label, reasoning)
    vals = defaultdict(list)
    cond = defaultdict(list)   # executed_exfil among episodes that COMPLETED the benign task
    files = sorted(glob.glob(args.glob))
    for fp in files:
        d = json.load(open(fp, encoding="utf-8"))
        for r in d.get("rows", []):
            if r.get("errored"):                      # drop episodes that hit a server/API error
                continue
            if args.exclude_blatant and r.get("framing") == "blatant":
                continue
            if r.get("framing") == "clean":           # clean tasks aren't attacks
                continue
            vals[(r["label"], r["reasoning"])].append(1 if r.get(args.metric) else 0)
            if r.get("benign_completed"):
                cond[(r["label"], r["reasoning"])].append(1 if r.get("executed_exfil") else 0)

    print(f"Pooled {len(files)} file(s). metric = {args.metric}"
          f"{'  (blatant excluded)' if args.exclude_blatant else ''}")
    labels = sorted({lbl for (lbl, _) in vals})
    print(f"\n{'label':<16}{'reasoning':<10}{'n':>5}{'rate':>7}{'95% CI':>18}")
    print("-" * 56)
    for lbl in labels:
        for reasoning in (False, True):
            v = vals[(lbl, reasoning)]
            m, lo, hi = boot_ci(v)
            print(f"{lbl:<16}{str(reasoning):<10}{len(v):>5}{m:>7.2f}   [{lo:.2f}, {hi:.2f}]")

    sg, ab = args.safeguarded_label, args.abliterated_label
    print("\n--- SAFEGUARDS effect:  abliterated - safeguarded ---")
    for reasoning in (False, True):
        a, b = vals[(ab, reasoning)], vals[(sg, reasoning)]
        if a and b:
            diff, lo, hi = boot_diff(a, b)
            print(f"reasoning={str(reasoning):<5} delta={diff:+.2f}  95% CI [{lo:+.2f}, {hi:+.2f}]  -> {_sig(lo, hi)}")

    print("\n--- REASONING effect (ON - OFF), within each model ---")
    for lbl in labels:
        on, off = vals[(lbl, True)], vals[(lbl, False)]
        if on and off:
            diff, lo, hi = boot_diff(on, off)
            print(f"{lbl:<16} delta={diff:+.2f}  95% CI [{lo:+.2f}, {hi:+.2f}]  -> {_sig(lo, hi)}")

    # Capability-controlled: among episodes where the model COMPLETED the benign task, how often
    # did it also leak? Separates "safer" from "less capable" (the pilot's main confound).
    print("\n--- VERIFIED EXFIL conditioned on benign completion (capability-controlled) ---")
    print(f"{'label':<16}{'reasoning':<10}{'n_done':>7}{'leak|done':>11}{'95% CI':>16}")
    print("-" * 60)
    for lbl in labels:
        for reasoning in (False, True):
            v = cond[(lbl, reasoning)]
            m, lo, hi = boot_ci(v)
            print(f"{lbl:<16}{str(reasoning):<10}{len(v):>7}{m:>11.2f}   [{lo:.2f}, {hi:.2f}]")
    for reasoning in (False, True):
        a, b = cond[(ab, reasoning)], cond[(sg, reasoning)]
        if a and b:
            diff, lo, hi = boot_diff(a, b)
            print(f"  safeguards effect reasoning={str(reasoning):<5} delta={diff:+.2f}  "
                  f"95% CI [{lo:+.2f}, {hi:+.2f}]  -> {_sig(lo, hi)}")


if __name__ == "__main__":
    main()
