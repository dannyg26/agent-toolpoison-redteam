"""Select the held-out comparison cases by metadata only; never inspects task text or model outcomes.

Inventory: the 200 sampled held-out rows in the frozen cases.json (`test`), not the declared test split. Those rows
represent 65 of the 68 declared held-out user tasks; after removing the pilot's 10 user tasks, 55 remain. Each
case is an existing frozen row (user task, injection goal, recorded vectors).

Rules (fixed before any held-out outcome of this study exists):
- 8 cases per suite, 32 in all, each on a distinct user task not used by the pilot (32 distinct user-task clusters).
- Within a suite, rows are taken in SHA-256 rank order ("heldout-2028|<case_id>"), always choosing the row whose
  injection goal has been used least so far (ties broken by rank). Goals repeat only when a suite has fewer than
  8 goals (Slack has 5, travel 7).
- Blocks: within each suite, the first 4 chosen cases go to block 1 and the next 4 to block 2, so each block has
  4 cases per suite. Block order is counterbalanced by the runner.
- Capability tasks: 3 benign development user tasks per suite (12), in rank order, excluding the pilot's two
  capability tasks. Target compatibility reuses the pilot's two development cases.

    python stage_b/select_heldout_cases.py [--check]
"""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITES = ("banking", "slack", "travel", "workspace")
PER_SUITE = 8
PER_BLOCK = 4
CAPABILITY_PER_SUITE = 3
SALT = "heldout-2028|"


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def rank(case_id):
    return hashlib.sha256((SALT + case_id).encode()).hexdigest()


def build(source=None, pilot=None):
    source = source or json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    pilot = pilot or json.loads((HERE / "cases_pilot.json").read_text(encoding="utf-8"))
    pilot_users = {(c["suite"], c["user_task"]) for c in pilot["test"]}
    pilot_capability = {tuple(cid.split("/")[:2]) for cid in pilot["capability_case_ids"]}
    test, blocks = [], {"block1": [], "block2": []}
    for suite in SUITES:
        rows = sorted((c for c in source["test"] if c["suite"] == suite
                       and (suite, c["user_task"]) not in pilot_users), key=lambda c: rank(c["case_id"]))
        used_users, goal_count, chosen = set(), {}, []
        while len(chosen) < PER_SUITE:
            open_rows = [c for c in rows if c["user_task"] not in used_users]
            if not open_rows:
                raise ValueError(f"not enough unused held-out user tasks in {suite}")
            best = min(open_rows, key=lambda c: (goal_count.get(c["injection_task"], 0), rank(c["case_id"])))
            chosen.append(best)
            used_users.add(best["user_task"])
            goal_count[best["injection_task"]] = goal_count.get(best["injection_task"], 0) + 1
        for i, case in enumerate(chosen):
            blocks["block1" if i < PER_BLOCK else "block2"].append(case["case_id"])
        test.extend(chosen)
    capability = []
    for suite in SUITES:
        by_user = {}
        for c in sorted((c for c in source["dev"] if c["suite"] == suite), key=lambda c: rank(c["case_id"])):
            if (suite, c["user_task"]) not in pilot_capability:
                by_user.setdefault(c["user_task"], c)      # one development row per user task, best rank
        picked = sorted(by_user.values(), key=lambda c: rank(c["case_id"]))[:CAPABILITY_PER_SUITE]
        if len(picked) != CAPABILITY_PER_SUITE:
            raise ValueError(f"not enough development user tasks for capability in {suite}")
        capability.extend(picked)
    compat_ids = list(pilot["compatibility_case_ids"])
    compat = [c for c in source["dev"] if c["case_id"] in compat_ids]
    dev = {c["case_id"]: c for c in capability + compat}
    return {"benchmark_version": source["benchmark_version"], "salt": SALT,
            "source_inventory_sha256": canonical_hash(source), "pilot_cases_sha256": canonical_hash(pilot),
            "inventory": "cases.json sampled held-out rows minus the pilot's user tasks",
            "selection": "metadata-only; distinct unused user tasks; least-used goal first; rank tie-break",
            "test": sorted(test, key=lambda c: c["case_id"]),
            "blocks": {k: sorted(v) for k, v in blocks.items()},
            "dev": sorted(dev.values(), key=lambda c: c["case_id"]),
            "capability_case_ids": sorted(c["case_id"] for c in capability),
            "compatibility_case_ids": compat_ids}


def describe(data):
    lines = [f"held-out selection: {len(data['test'])} cases, "
             f"{len({(c['suite'], c['user_task']) for c in data['test']})} distinct user-task clusters"]
    for suite in SUITES:
        rows = [c for c in data["test"] if c["suite"] == suite]
        goals = {}
        for c in rows:
            goals[c["injection_task"]] = goals.get(c["injection_task"], 0) + 1
        repeats = {g: n for g, n in goals.items() if n > 1}
        lines.append(f"  {suite}: {len(rows)} cases, {len(goals)} goals, repeated goals {repeats or 'none'}")
    lines.append(f"  blocks: {', '.join(f'{k} {len(v)}' for k, v in data['blocks'].items())}; "
                 f"capability tasks {len(data['capability_case_ids'])}; compatibility {len(data['compatibility_case_ids'])}")
    lines.append(f"case metadata SHA-256: {canonical_hash(data)}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    data = build()
    path = HERE / "cases_heldout.json"
    if args.check:
        if json.loads(path.read_text(encoding="utf-8")) != data:
            raise SystemExit("held-out selection does not reproduce")
    else:
        path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(describe(data))


if __name__ == "__main__":
    main()
