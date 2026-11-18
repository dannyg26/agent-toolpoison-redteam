"""Select the framing follow-up's cases by metadata only; never inspects task text or any model outcome.

Inventory: the frozen cases.json sampled held-out rows whose user task was used by NEITHER the pilot NOR the
completed held-out study: 23 user tasks (banking 0, slack 4, travel 4, workspace 15). Every one is used, one case
per user task: 23 distinct user-task clusters, never evaluated in any condition. For each user task the row is
chosen in SHA-256 rank order ("followup-2026|<case_id>") taking the least-used injection goal in its suite first.
Banking is absent (all its held-out user tasks were used); this coverage gap is disclosed, not filled by reuse.
Blocks: suites split as evenly as possible (slack 2/2, travel 2/2, workspace 8/7), by rank.

    python stage_b/select_followup_cases.py [--check]
"""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITES = ("banking", "slack", "travel", "workspace")
SALT = "followup-2026|"


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def rank(case_id):
    return hashlib.sha256((SALT + case_id).encode()).hexdigest()


def build():
    load = lambda n: json.loads((HERE / n).read_text(encoding="utf-8"))
    source, pilot, held = load("cases.json"), load("cases_pilot.json"), load("cases_heldout.json")
    used = {(c["suite"], c["user_task"]) for c in pilot["test"] + held["test"]}
    test, blocks = [], {"block1": [], "block2": []}
    for suite in SUITES:
        rows = sorted((c for c in source["test"] if c["suite"] == suite and (suite, c["user_task"]) not in used),
                      key=lambda c: rank(c["case_id"]))
        users = sorted({c["user_task"] for c in rows}, key=lambda u: min(rank(c["case_id"]) for c in rows
                                                                         if c["user_task"] == u))
        goal_count, chosen = {}, []
        for _ in users:
            open_rows = [c for c in rows if c["user_task"] not in {x["user_task"] for x in chosen}]
            best = min(open_rows, key=lambda c: (goal_count.get(c["injection_task"], 0), rank(c["case_id"])))
            chosen.append(best)
            goal_count[best["injection_task"]] = goal_count.get(best["injection_task"], 0) + 1
        half = (len(chosen) + 1) // 2
        for i, case in enumerate(chosen):
            blocks["block1" if i < half else "block2"].append(case["case_id"])
        test.extend(chosen)
    return {"benchmark_version": source["benchmark_version"], "salt": SALT,
            "source_inventory_sha256": canonical_hash(source),
            "excluded_user_tasks": "every user task used by the pilot or the completed held-out study",
            "selection": "metadata-only; all remaining represented held-out user tasks, one case each",
            "test": sorted(test, key=lambda c: c["case_id"]),
            "blocks": {k: sorted(v) for k, v in blocks.items()},
            "dev": [], "capability_case_ids": [], "compatibility_case_ids": list(held["compatibility_case_ids"])}


def describe(d):
    lines = [f"follow-up selection: {len(d['test'])} cases, "
             f"{len({(c['suite'], c['user_task']) for c in d['test']})} distinct user-task clusters"]
    for s in SUITES:
        rows = [c for c in d["test"] if c["suite"] == s]
        g = {}
        for c in rows:
            g[c["injection_task"]] = g.get(c["injection_task"], 0) + 1
        lines.append(f"  {s}: {len(rows)} cases, {len(g)} goals, repeated {({k: v for k, v in g.items() if v > 1}) or 'none'}")
    lines.append("  blocks: " + ", ".join(f"{k} {len(v)}" for k, v in d["blocks"].items()))
    lines.append(f"case metadata SHA-256: {canonical_hash(d)}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    data = build()
    held = json.loads((HERE / "cases_heldout.json").read_text(encoding="utf-8"))
    data["dev"] = [c for c in held["dev"] if c["case_id"] in data["compatibility_case_ids"]]
    path = HERE / "cases_followup.json"
    if args.check:
        if json.loads(path.read_text(encoding="utf-8")) != data:
            raise SystemExit("follow-up selection does not reproduce")
    else:
        path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(describe(data))


if __name__ == "__main__":
    main()
