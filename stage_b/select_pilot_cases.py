"""Select the small pilot by metadata only; never inspect task text or model outcomes.

Keeps the existing 200/40 case inventory unchanged. Ten held-out cases have distinct user-task
clusters and coverage 3 banking, 3 workspace, 2 slack, 2 travel. Run --check before serving models.
"""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUOTAS = {"banking": 3, "workspace": 3, "slack": 2, "travel": 2}
# Selected from existing development tasks by reference-solution call count, not model outcomes.
# Validated against the pinned benchmark in test_pilot.py before a paid run.
CAPABILITY_USERS = {("banking", "user_task_11"), ("workspace", "user_task_19")}


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def rank(case):
    return hashlib.sha256(("budget-pilot-2027|" + case["case_id"]).encode()).hexdigest()


def build(source=None):
    source = source or json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    chosen = []
    for suite, quota in QUOTAS.items():
        used_users, used_injections = set(), set()
        candidates = sorted((c for c in source["test"] if c["suite"] == suite), key=rank)
        for case in candidates:
            if case["user_task"] in used_users or case["injection_task"] in used_injections:
                continue
            chosen.append(case)
            used_users.add(case["user_task"])
            used_injections.add(case["injection_task"])
            if len(used_users) == quota:
                break
        if len(used_users) != quota:
            raise ValueError(f"not enough distinct task/goal pairs in {suite}")
    # Two public development cases for target compatibility, separate from the held-out ten.
    dev = [min((c for c in source["dev"] if c["suite"] == s), key=rank)
           for s in ("banking", "workspace")]
    capability = []
    for suite, user in sorted(CAPABILITY_USERS):
        candidates = [c for c in source["dev"] if c["suite"] == suite and c["user_task"] == user]
        if not candidates:
            raise ValueError(f"capability task is not in the development inventory: {suite}/{user}")
        capability.append(min(candidates, key=rank))
    all_dev = {c["case_id"]: c for c in dev + capability}
    return {"benchmark_version": source["benchmark_version"], "seed": 2027,
            "source_inventory_sha256": canonical_hash(source),
            "selection": "metadata-only; unique user task and injection goal within suite; fixed quotas",
            "test": sorted(chosen, key=lambda c: c["case_id"]),
            "dev": sorted(all_dev.values(), key=lambda c: c["case_id"]),
            "compatibility_case_ids": [c["case_id"] for c in dev],
            "capability_case_ids": [c["case_id"] for c in capability]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    data = build()
    path = HERE / "cases_pilot.json"
    if args.check:
        if json.loads(path.read_text(encoding="utf-8")) != data:
            raise SystemExit("pilot selection does not reproduce")
    else:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"pilot selection: {len(data['test'])} held-out cases, 10 distinct user-task clusters")
    print(f"case metadata SHA-256: {canonical_hash(data)}")


if __name__ == "__main__":
    main()
