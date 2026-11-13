"""Render the RESULTS.md tables straight from results_numbers.json and the calibration files, so that
every displayed number is rounded once, directly from full precision.

    python make_tables.py            # prints the tables as Markdown
"""
from __future__ import annotations
import json, sys
sys.stdout.reconfigure(encoding="utf-8")

ARMS_MAIN = ["no-attacker", "aligned-plain", "abliterated-plain", "aligned-redteam", "abliterated-redteam"]
ARMS_E1 = ["no-attacker", "abliterated-plain", "trained-redteam", "aligned-redteam", "abliterated-redteam"]
LABEL = {"no-attacker": "no-attacker (just ask)", "aligned-redteam": "**aligned-redteam**",
         "trained-redteam": "**trained-redteam**"}


def r2(x):
    return f"{x:.2f}"


def sgn(x, nd=2):
    s = f"{x:+.{nd}f}"
    return s.replace("-", "−")


def interval(lo, hi, nd=2):
    return f"[{sgn(lo, nd)}, {sgn(hi, nd)}]"


def asr_cell(v):
    return f"{r2(v[0])} [{r2(v[1])}, {r2(v[2])}]"


def p_fmt(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}".rstrip("0").rstrip(".") if p >= 0.01 else f"{p:.4f}"


def asr_table(d, study, arms):
    out = ["| arm | A: Qwen2.5-7B | B: Llama-3.1-8B |", "|---|---|---|"]
    for a in arms:
        out.append(f"| {LABEL.get(a, a)} | {asr_cell(d['A'][study]['asr'][a])} | {asr_cell(d['B'][study]['asr'][a])} |")
    return "\n".join(out)


def hyp(d, study, T, hid, key="hypotheses"):
    return next(h for h in d[T][study][key] if h["id"] == hid)


def hyp_cell(h):
    est = f"{sgn(h['d'])} {interval(h['lo'], h['hi'])}"
    if h["kind"] == "margin":
        return f"{est}; one-sided p (d ≥ +0.05) {p_fmt(h['margin_p'])}"
    if h["holm"] is not None:
        return f"{est}, p {p_fmt(h['p'])}, Holm {p_fmt(h['holm'])}"
    return f"{est}, p {p_fmt(h['p'])}"


def main():
    d = json.load(open("results_numbers.json"))
    print("### Main study ASR\n")
    print(asr_table(d, "main", ARMS_MAIN))
    print("\n### Main study hypotheses\n")
    for hid in ("H1", "H2", "H3", "H4a", "H4b", "H4c", "X1", "X2"):
        a, b = hyp(d, "main", "A", hid), hyp(d, "main", "B", hid)
        print(f"| {hid} {a['x']} − {a['y']} | {hyp_cell(a)} | {hyp_cell(b)} | A: {a['verdict']}; B: {b['verdict']} |")
    print("\n### E1 ASR\n")
    print(asr_table(d, "e1", ARMS_E1))
    print("\n### E1 hypotheses\n")
    for hid in ("E1-H5", "E1-H6", "E1-floor"):
        a, b = hyp(d, "e1", "A", hid), hyp(d, "e1", "B", hid)
        print(f"| {hid} {a['x']} − {a['y']} | {hyp_cell(a)} | {hyp_cell(b)} | A: {a['verdict']}; B: {b['verdict']} |")
    print("\n### Sensitivity (H1, E1-H5, E1-H6)\n")
    for k in ("main", "main_per_arm_miss", "main_agent1", "main_agent2", "main_flip_abl_plain"):
        a, b = hyp(d, k, "A", "H1"), hyp(d, k, "B", "H1")
        h2a, h2b = hyp(d, k, "A", "H2"), hyp(d, k, "B", "H2")
        print(f"| {k} | {sgn(a['d'])} {interval(a['lo'], a['hi'])} ({a['verdict']}) | "
              f"{sgn(b['d'])} {interval(b['lo'], b['hi'])} ({b['verdict']}) | H2 Holm A {p_fmt(h2a['holm'])}, "
              f"B {p_fmt(h2b['holm'])} |")
    for k in ("e1", "e1_per_arm_miss", "e1_agent1", "e1_agent2"):
        row = []
        for hid in ("E1-H5", "E1-H6", "E1-floor"):
            a, b = hyp(d, k, "A", hid), hyp(d, k, "B", hid)
            row.append(f"{hid} A {sgn(a['d'])} {interval(a['lo'], a['hi'])} / B {sgn(b['d'])} {interval(b['lo'], b['hi'])}"
                       f" (B: {b['verdict']})")
        print(f"| {k} | " + " | ".join(row) + " |")
    for T in "AB":
        m = d[T]["h1_miss_range"]
        print(f"least favourable miss rates {T}: H1 point {sgn(m['h1_at_adverse_extreme'])}; per-arm point "
              f"{sgn(m['h1_at_per_arm_point'])}; flip count {d[T]['flip_count']}; clustering "
              f"{d[T]['descriptives']['pooled_audit_clustering']}")


if __name__ == "__main__":
    main()
