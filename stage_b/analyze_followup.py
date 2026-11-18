"""Framing follow-up analysis (EXPLORATORY; frozen before collection). No model calls.

    python stage_b/analyze_followup.py report --download <dir> [--output <json>]
    python stage_b/analyze_followup.py precision           # planning: expected interval widths

Per case and condition: benchmark success within 3 candidates, classified by the completed study's unchanged
heldout_tools.status. Conditions: {abliterated, aligned} x {authorized, neutral}, all on the same 23 cases.

PRIMARY (exploratory estimand, no hypothesis test, no verdict):
  interaction per case  d = (S_abl,neutral - S_aligned,neutral) - (S_abl,authorized - S_aligned,authorized),
  each S in {0,1}; reported as the mean of d over cases complete in all four conditions, with a 95% percentile
  bootstrap interval over cases (10,000 resamples, seed 2026), labelled conditional on those cases; plus the
  range of the mean over the planned 23 when every missing S is set to its most favourable / least favourable
  value (bounds). The interval is descriptive: the study is not powered for the interaction.
SECONDARY (descriptive): the four success rates over the planned cases (observed counts, Wilson interval among
  observed, bounds); the two simple effects (abliterated minus aligned within each framing) and the two framing
  effects (neutral minus authorized within each model) as paired count tables; the attacker-refusal ENDPOINT per
  condition: a pattern-matched refusal statement OUTSIDE the insertion (rule category A or D_mixed), on the first
  attempt and in any attempt per campaign, each over the planned 23 (observed counts, Wilson among observed,
  bounds; unknowns never counted as "no refusal"); separately, D_empty (empty answers), C, refusal patterns
  inside insertions, missing attacker text, and the reasoning flag.
NOT CLAIMED: that refusal mediates success (correlation is not mediation); equivalence; anything about genuinely
  unauthorized deployment (both framings still name a simulated benchmark and a red-team role); a semantic
  absence of refusal (the endpoint is a pattern match); an explanation of the completed study's inconclusive
  result (this measures sensitivity to the explicit authorization phrase only).
Robustness: results and traces are read interruption-safely; a missing or partial trace never removes a benchmark
  outcome and never prevents the 23-case report.
"""
import argparse
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_heldout as AH  # noqa: E402  (wilson, rate_summary: unchanged)
import audit_refusals as AR  # noqa: E402
import followup_tools as FT  # noqa: E402
import heldout_tools as HT  # noqa: E402

CONDS = [("abliterated", "authorized"), ("abliterated", "neutral"), ("aligned", "authorized"), ("aligned", "neutral")]
SEED, B = 2026, 10000


def label(model, framing):
    return f"{model}-{framing}"


def bootstrap_mean(values, seed=SEED, reps=B):
    if not values:
        return None
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choice(values) for _ in range(n)) / n for _ in range(reps))
    return [means[int(0.025 * reps)], means[int(0.975 * reps) - 1]]


def interaction(s):
    return (s[("abliterated", "neutral")] - s[("aligned", "neutral")]) - (
        s[("abliterated", "authorized")] - s[("aligned", "authorized")])


def primary(states):
    """states: list over planned cases of {cond: 'success'|'no_observed_success'|'incomplete'}."""
    complete = [{c: int(st[c] == "success") for c in CONDS} for st in states
                if all(st[c] != "incomplete" for c in CONDS)]
    ds = [interaction(s) for s in complete]
    lo_vals, hi_vals = [], []
    for st in states:          # bounds over the planned cases: choose each missing S to minimise / maximise d
        known = {c: int(st[c] == "success") for c in CONDS if st[c] != "incomplete"}
        sign = {("abliterated", "neutral"): 1, ("aligned", "neutral"): -1,
                ("abliterated", "authorized"): -1, ("aligned", "authorized"): 1}
        lo = {c: known.get(c, 0 if sign[c] > 0 else 1) for c in CONDS}
        hi = {c: known.get(c, 1 if sign[c] > 0 else 0) for c in CONDS}
        lo_vals.append(interaction(lo))
        hi_vals.append(interaction(hi))
    n = len(states)
    return {"planned_cases": n, "complete_cases": len(complete),
            "mean_interaction_complete_cases_conditional": (sum(ds) / len(ds)) if ds else None,
            "bootstrap_95ci_complete_cases_conditional": bootstrap_mean(ds),
            "distribution_of_d": {str(v): ds.count(v) for v in (-2, -1, 0, 1, 2)},
            "bounds_mean_over_planned": [sum(lo_vals) / n, sum(hi_vals) / n] if n else None,
            "note": "exploratory; no hypothesis test; interval conditional on complete cases"}


def paired_counts(states, a, b):
    pairs = [(st[a] == "success", st[b] == "success") for st in states
             if st[a] != "incomplete" and st[b] != "incomplete"]
    return {"first": "/".join(a), "second": "/".join(b), **AH.paired_summary(pairs)}


def report(download):
    config, cases = FT.load_config(), FT.load("cases_followup.json")
    diag, rows = [], {}
    for c in CONDS:
        rows[c] = {}
        for block in cases["blocks"]:
            for r in HT.records(Path(download) / f"runs_{block}" / f"test__adaptive__{label(*c)}__gemma.jsonl", diag):
                rows[c][r.get("case_id")] = r
    per_case, states = [], []
    for case in cases["test"]:
        st, row = {}, {"case_id": case["case_id"], "suite": case["suite"]}
        for c in CONDS:
            state, reason = HT.status(rows[c].get(case["case_id"]), config["candidate_budget"])
            st[c] = state
            row[label(*c)] = {"state": state, "reason": reason,
                              "success_at": (rows[c].get(case["case_id"]) or {}).get("success_at")}
        states.append(st)
        per_case.append(row)
    out = {"nature": "exploratory", "primary_interaction": primary(states), "per_case": per_case}
    out["success_rates_over_planned"] = {label(*c): AH.rate_summary(
        [True if st[c] == "success" else False if st[c] == "no_observed_success" else "incomplete" for st in states])
        for c in CONDS}
    out["simple_effects_abliterated_minus_aligned"] = {
        f: paired_counts(states, ("abliterated", f), ("aligned", f)) for f in config["framings"]}
    out["framing_effects_neutral_minus_authorized"] = {
        m: paired_counts(states, (m, "neutral"), (m, "authorized")) for m in config["attacker_labels"]}
    out["attacker_refusal_endpoint"] = refusal_summary(download, cases, diag)
    clean = {r["key"]: r for r in HT.records(Path(download) / "baselines" / "test__no_attack__none__gemma.jsonl", diag)}
    out["clean_utility"] = AH.rate_summary([AH._episode_outcome(clean.get(f"{c['suite']}/{c['user_task']}"), "utility")
                                            for c in cases["test"]])
    out["file_diagnostics"] = diag
    ev = Path(download) / "supervisor_events.jsonl"
    out["supervisor_events"] = HT.records_plain(ev) if ev.exists() else []
    return out


def refusal_summary(download, cases, diag):
    """Narrowed endpoint (audit_refusals.endpoint_summary) per condition over the PLANNED cases; counts only, never
    text. Interruption-safe: a missing/partial trace leaves that attacker text unknown; a corrupt file makes only
    that condition's refusal summary unavailable. Benchmark outcomes are never read from or altered by this."""
    planned = [c["case_id"] for c in cases["test"]]
    summary = {}
    for c in CONDS:
        gens, d = [], []
        try:
            for block in cases["blocks"]:
                gens += AR.load([str(Path(download) / f"runs_{block}")], "followup", d, arm=label(*c))
            summary[label(*c)] = AR.endpoint_summary(gens, planned)
        except HT.CorruptRecords as exc:
            summary[label(*c)] = {"unavailable": f"corrupt file: {exc}"}
        seen = {json.dumps({k: v for k, v in x.items() if k != "part"}, sort_keys=True) for x in diag}
        for x in d:                       # result-file diagnostics were already recorded by the primary loader
            if json.dumps(x, sort_keys=True) not in seen:
                diag.append({**x, "part": "attacker text"})
                seen.add(json.dumps(x, sort_keys=True))
    return summary


def precision():
    """Planning only: simulated width of the bootstrap interval for the interaction at n=23 under simple
    scenarios (case-level random effect induces within-case correlation). Not a power analysis."""
    import math
    rng = random.Random(7)
    rows = []
    for rho_label, sd in (("low within-case correlation", 0.3), ("high within-case correlation", 1.5)):
        for p in (0.3, 0.5):
            widths = []
            for _ in range(200):
                ds = []
                for _ in range(23):
                    u = rng.gauss(0, sd)
                    base = math.log(p / (1 - p)) + u
                    s = {c: int(rng.random() < 1 / (1 + math.exp(-base))) for c in CONDS}
                    ds.append(interaction(s))
                ci = bootstrap_mean(ds, seed=rng.randrange(10 ** 6), reps=1000)
                widths.append(ci[1] - ci[0])
            rows.append({"scenario": rho_label, "success_rate": p, "median_95ci_width": round(sorted(widths)[100], 3)})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["report", "precision"])
    ap.add_argument("--download")
    ap.add_argument("--output")
    args = ap.parse_args()
    if args.action == "precision":
        for r in precision():
            print(json.dumps(r))
        return
    if not args.download:
        ap.error("--download is required")
    result = report(args.download)
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result["primary_interaction"], indent=1))


if __name__ == "__main__":
    main()
