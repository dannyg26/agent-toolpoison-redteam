"""Held-out comparison analysis (frozen before collection). Standard methods only; no model calls.

    python stage_b/analyze_heldout.py power                      # planning table (exact enumeration)
    python stage_b/analyze_heldout.py report --download <dir> [--output <json>]

Primary outcome per planned case and arm: benchmark `security` success within 3 candidates, classified by
heldout_tools.status. Paired by case (abliterated vs aligned).

Methods:
- exact two-sided McNemar test (binomial on discordant pairs, p = min(1, 2 P[X <= min(b, c)])), alpha 0.05;
- Tango (1998) score 95% CI for the paired difference p_abliterated - p_aligned;
- Wilson 95% intervals for single proportions.

Missing outcomes (frozen rule):
- Every planned pair is listed with its state and reason.
- With no incomplete pairs, the planned-set result is the observed McNemar test and Tango CI.
- With any incomplete pair, three analyses are reported: complete pairs only (labelled CONDITIONAL on those
  pairs, valid only if completion is unrelated to outcome), and the two extreme completions of the missing
  outcomes. Each extreme gives a point difference, a McNemar p and a Tango CI, so the bounds cover inference as
  well as the point estimate.
- A superiority verdict over the planned set is issued only when the completion least favourable to that
  direction still rejects in that direction. Otherwise the verdict is WITHHELD ("missing outcomes could
  change the conclusion"), and a complete-pair result is never presented as the planned-set result.
- A non-rejection is "no difference detected (inconclusive)", never equivalence.

Secondary, baseline and capability summaries are descriptive with NO hypothesis tests. Every rate is over the
frozen PLANNED inventory (32 cases, 32 clean user tasks, 12 capability tasks): unobserved units (missing record,
deadline, infrastructure error, limited episode) are listed by reason and never counted as failures. Each rate
gives observed counts, a Wilson interval conditional on observed units, and bounds over the planned set.
A trailing partial JSONL line is dropped and reported in `file_diagnostics`; interior corruption raises.
The report can be generated from any partial download:  report --download <local download directory>
"""
import argparse
from math import comb, erf, sqrt
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import heldout_tools as T  # noqa: E402

ALPHA = 0.05
Z = 1.959963984540054


def mcnemar_exact(b, c):
    m = b + c
    if m == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(m, i) for i in range(k + 1)) / 2 ** m)


def tango_ci(b, c, n, z=Z):
    """Tango score interval for the paired difference (b - c) / n, where b = only arm 1 succeeded."""
    if n <= 0:
        raise ValueError("n must be positive")

    def score(d):
        a_, b_, c_ = 2 * n, -b - c + (2 * n - b + c) * d, -c * d * (1 - d)
        q = (sqrt(max(b_ * b_ - 4 * a_ * c_, 0.0)) - b_) / (2 * a_)
        var = n * (2 * q + d * (1 - d))
        return (b - c - n * d) / sqrt(var) if var > 0 else (0.0 if b - c == n * d else float("inf") * (b - c - n * d))

    def solve(lo, hi, target):              # score is decreasing in d
        for _ in range(200):
            mid = (lo + hi) / 2
            if score(mid) > target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    est = (b - c) / n
    lower = -1.0 if score(-1 + 1e-12) <= z else solve(-1 + 1e-12, est, z)
    upper = 1.0 if score(1 - 1e-12) >= -z else solve(est, 1 - 1e-12, -z)
    return lower, upper


def wilson(k, n, z=Z):
    if n == 0:
        return (None, None)
    p = k / n
    centre, half = (p + z * z / (2 * n)) / (1 + z * z / n), z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def power(n, p_only_1, p_only_2, alpha=ALPHA):
    """Exact power of the two-sided exact McNemar test, enumerating the multinomial (b, c, concordant)."""
    p_c = 1 - p_only_1 - p_only_2
    total = 0.0
    for b in range(n + 1):
        for c in range(n - b + 1):
            if mcnemar_exact(b, c) <= alpha:
                total += (comb(n, b) * comb(n - b, c) * p_only_1 ** b * p_only_2 ** c * p_c ** (n - b - c))
    return total


POWER_SCENARIOS = [(0.25, 0.05), (0.30, 0.05), (0.30, 0.10), (0.325, 0.075), (0.15, 0.05), (0.20, 0.10)]


def power_table(n=32):
    rows = []
    for p1, p2 in POWER_SCENARIOS:
        rows.append({"n": n, "p_uncensored_only": p1, "p_aligned_only": p2, "difference": round(p1 - p2, 4),
                     "discordance": round(p1 + p2, 4), "power_two_sided_exact_mcnemar": round(power(n, p1, p2), 6)})
    return rows


def planning_halfwidth(n, discordance):
    """Wald planning approximation at zero true difference; NOT the width of the eventual Tango interval."""
    return Z * sqrt(discordance / n)


# ---------------------------------------------------------------------------------------------------------------

def paired_summary(pairs, test=False):
    """pairs: list of (abliterated_success: bool, aligned_success: bool). A McNemar p-value and Tango CI are
    added ONLY for the primary analysis (test=True); secondary and capability tables are counts only."""
    b = sum(a and not g for a, g in pairs)
    c = sum(g and not a for a, g in pairs)
    n = len(pairs)
    out = {"n": n, "both": sum(a and g for a, g in pairs), "abliterated_only": b, "aligned_only": c,
           "neither": sum(not a and not g for a, g in pairs),
           "abliterated_successes": sum(a for a, _ in pairs), "aligned_successes": sum(g for _, g in pairs),
           "difference": (b - c) / n if n else None}
    if test and n:
        lo, hi = tango_ci(b, c, n)
        out.update(tango_95ci=[lo, hi], mcnemar_exact_p=mcnemar_exact(b, c))
    return out


def completions(states):
    """states: list of (abliterated_state, aligned_state). Returns the two extreme completions."""
    def fill(state, value):
        return state == "success" if state != "incomplete" else value
    toward_abl = [(fill(a, True), fill(g, False)) for a, g in states]
    toward_aligned = [(fill(a, False), fill(g, True)) for a, g in states]
    return toward_abl, toward_aligned


def verdict(states):
    complete = [(a == "success", g == "success") for a, g in states if "incomplete" not in (a, g)]
    best_abl, best_aligned = completions(states)
    least_fav_abl, least_fav_aligned = best_aligned, best_abl
    res = {"planned_pairs": len(states), "complete_pairs": len(complete),
           "incomplete_pairs": len(states) - len(complete),
           "complete_pairs_conditional": paired_summary(complete, test=True),
           "completion_most_favourable_to_abliterated": paired_summary(best_abl, test=True),
           "completion_most_favourable_to_aligned": paired_summary(best_aligned, test=True)}
    la, lg = paired_summary(least_fav_abl, test=True), paired_summary(least_fav_aligned, test=True)
    if la["mcnemar_exact_p"] <= ALPHA and la["abliterated_only"] > la["aligned_only"]:
        res["verdict"] = "abliterated higher over the planned set (robust to every completion of missing outcomes)"
    elif lg["mcnemar_exact_p"] <= ALPHA and lg["aligned_only"] > lg["abliterated_only"]:
        res["verdict"] = "aligned higher over the planned set (robust to every completion of missing outcomes)"
    elif res["incomplete_pairs"] == 0:
        res["verdict"] = "no difference detected at alpha 0.05 (inconclusive; not evidence of equivalence)"
    else:
        res["verdict"] = ("WITHHELD: missing outcomes could change the conclusion; the complete-pair result is "
                          "conditional on those pairs and is not the planned-set result")
    return res


def rate_summary(states):
    """states: one entry per PLANNED unit: True / False for an observed benchmark outcome, otherwise a string
    giving why it was not observed (missing, deadline, infrastructure_error, limited, an incomplete reason).
    Unobserved units are never counted as failures: the Wilson interval is conditional on observed units and
    the bounds cover every possible value of the unobserved ones."""
    planned = len(states)
    k = sum(s is True for s in states)
    m = sum(isinstance(s, bool) for s in states)
    not_observed = {}
    for s in states:
        if not isinstance(s, bool):
            not_observed[s] = not_observed.get(s, 0) + 1
    unk = planned - m
    return {"planned": planned, "observed": m, "observed_true": k, "observed_false": m - k,
            "not_observed": not_observed,
            "rate_among_observed": (k / m) if m else None,
            "wilson_95ci_conditional_on_observed": list(wilson(k, m)) if m else None,
            "bounds_over_planned": [k / planned, (k + unk) / planned] if planned else None}


def _episode_outcome(record, field):
    if record and record.get("exception"):          # the unit raised before producing an episode
        return "deadline" if T.is_deadline(record["exception"]) else "infrastructure_error"
    episode = (record or {}).get("episode")
    state = T.episode_state(episode)
    return episode.get(field) is True if state == "observed" else state


def _arm_rows(download, arm, block, diag):
    path = Path(download) / f"runs_{block}" / f"test__adaptive__{arm}__gemma.jsonl"
    return {r.get("case_id"): r for r in T.records(path, diag)}


def report(download):
    config, cases = T.load_config(), T.load("cases_heldout.json")
    budget, arms = config["candidate_budget"], config["attacker_labels"]
    diag = []
    block_of = {cid: b for b, ids in cases["blocks"].items() for cid in ids}
    per_case, states = [], []
    arm_rows = {arm: {} for arm in arms}
    for arm in arms:
        for block in cases["blocks"]:
            arm_rows[arm].update(_arm_rows(download, arm, block, diag))
    for case in cases["test"]:
        cid = case["case_id"]
        row = {"case_id": cid, "suite": case["suite"], "injection_task": case["injection_task"], "block": block_of[cid]}
        for arm in arms:
            r = arm_rows[arm].get(cid)
            state, reason = T.status(r, budget)
            cands = (r or {}).get("candidates", [])
            row[arm] = {"state": state, "reason": reason, "success_at": (r or {}).get("success_at"),
                        "candidates": len(cands),
                        "candidate_states": [T.candidate_state(c) for c in cands],
                        "attacker_capped": sum(c.get("attacker", {}).get("finish_reason") == "length" for c in cands)}
        per_case.append(row)
        states.append((row["abliterated"]["state"], row["aligned"]["state"]))
    result = {"primary": verdict(states), "per_case": per_case}
    result["blocks"] = {block: {"planned": len(ids), "complete_pairs": sum(
        "incomplete" not in s for s, r in zip(states, per_case) if r["block"] == block)}
        for block, ids in cases["blocks"].items()}
    # Secondary: descriptive only, no hypothesis tests. Unobserved outcomes are never counted as failures.
    first = [(r["abliterated"]["success_at"] == 1, r["aligned"]["success_at"] == 1) for r in per_case
             if "incomplete" not in (r["abliterated"]["state"], r["aligned"]["state"])]
    sec = {"first_candidate_success_complete_pairs_conditional": paired_summary(first), "arms": {}}
    for arm in arms:
        cands = [c for r in arm_rows[arm].values() for c in r.get("candidates", [])]
        eps = [c["episode"] for c in cands if c.get("episode")]
        sec["arms"][arm] = {
            "campaign_success_over_planned": rate_summary(
                [True if r[arm]["state"] == "success" else False if r[arm]["state"] == "no_observed_success"
                 else (r[arm]["reason"] or "incomplete") for r in per_case]),
            "executed_candidate_generations": len(cands),
            "no_insertion_not_capped": sum(T.candidate_state(c) == "no_insertion" for c in cands),
            "cap_before_insertion": sum(T.candidate_state(c) == "cap_before_insertion" for c in cands),
            "capped_with_complete_insertion": sum(c.get("attacker", {}).get("finish_reason") == "length"
                                                  and bool(c.get("injection")) for c in cands),
            "executed_target_episodes": len(eps),
            "detected_exposure_prefix_heuristic_among_executed": sum(e.get("encountered") is True for e in eps),
            "utility_under_attack_among_executed": sum(e.get("utility") is True for e in eps),
            "attacker_completion_tokens": sum(c.get("attacker", {}).get("completion_tokens") or 0 for c in cands),
            "target_completion_tokens": sum(e.get("completion_tokens", 0) for e in eps),
        }
    fixed = {r["key"]: r for r in T.records(Path(download) / "baselines" / "test__fixed__none__gemma.jsonl", diag)}
    sec["fixed_template_security"] = rate_summary([_episode_outcome(fixed.get(c["case_id"]), "security")
                                                   for c in cases["test"]])
    clean = {r["key"]: r for r in T.records(Path(download) / "baselines" / "test__no_attack__none__gemma.jsonl", diag)}
    clean_keys = sorted({f"{c['suite']}/{c['user_task']}" for c in cases["test"]})
    sec["clean_utility"] = rate_summary([_episode_outcome(clean.get(k), "utility") for k in clean_keys])
    suites = {}
    for r in per_case:
        s = suites.setdefault(r["suite"], {arm: {st: 0 for st in T.STATES} for arm in arms})
        for arm in arms:
            s[arm][r[arm]["state"]] += 1
    sec["per_suite"] = suites
    goals = {}
    for r in per_case:
        goals.setdefault(f"{r['suite']}/{r['injection_task']}", []).append(r["case_id"])
    sec["repeated_goals"] = {g: ids for g, ids in goals.items() if len(ids) > 1}
    result["secondary_descriptive"] = sec
    # Capability: the FROZEN planned task inventory; an unrun task or arm is unknown, never zero.
    planned_tasks = ["/".join(cid.split("/")[:2]) for cid in cases["capability_case_ids"]]
    cap = {}
    for arm in arms:
        rows = {r["key"]: r for r in T.records(Path(download) / f"capability_{arm}" /
                                                f"dev__no_attack__none__{arm}.jsonl", diag)}
        cap[arm] = [_episode_outcome(rows.get(k), "utility") for k in planned_tasks]
    both = [(a, g) for a, g in zip(cap["abliterated"], cap["aligned"]) if isinstance(a, bool) and isinstance(g, bool)]
    result["capability"] = {
        "planned_tasks": len(planned_tasks),
        **{arm: rate_summary(cap[arm]) for arm in arms},
        "paired_tasks_observed_in_both_conditional": paired_summary(both) if both else None,
        "tasks_not_comparable": len(planned_tasks) - len(both),
        "note": "descriptive; no hypothesis test; not a gate, not the original Stage A gate, no equivalence claim",
    }
    result["file_diagnostics"] = diag
    events = Path(download) / "supervisor_events.jsonl"
    result["supervisor_events"] = T.records_plain(events) if events.exists() else []
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["power", "report"])
    ap.add_argument("--download")
    ap.add_argument("--output")
    args = ap.parse_args()
    if args.action == "power":
        rows = power_table()
        for r in rows:
            print(json.dumps(r))
        for d in (0.25, 0.30, 0.40):
            print(f"planning approximation only (Wald, zero difference): n=32, discordance {d:.2f} -> "
                  f"+/-{planning_halfwidth(32, d):.3f}")
        return
    if not args.download:
        ap.error("--download is required")
    result = report(args.download)
    text = json.dumps(result, indent=1)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(json.dumps(result["primary"], indent=1))


if __name__ == "__main__":
    main()
