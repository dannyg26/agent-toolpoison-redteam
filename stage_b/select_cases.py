"""Stage B case selection for AgentDojo (benchmark version v1.2.2, package agentdojo==0.1.35).

A case is (suite, user task, injection task). The split is by USER TASK within each suite, so every case built
on a user task lands in the same split as that task (plan §5). Test cases are drawn per suite, spread as evenly
as possible across that suite's injection tasks. Development cases are the only ones used to develop prompts.

Writes stage_b/cases.json. Deterministic: seed 2027, no model calls. Run:
    python stage_b/select_cases.py [--check]   (--check recomputes and compares with the committed file)
"""
import argparse, hashlib, json, random, sys, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
from agentdojo.attacks.base_attacks import BaseAttack
from agentdojo.task_suite.load_suites import get_suites

VERSION = "v1.2.2"
SEED = 2027
DEV_SHARE = 0.30          # share of each suite's user tasks reserved for development
TEST_PER_SUITE = 50       # 4 suites x 50 = 200 test cases (plan §5 target)
DEV_PER_SUITE = 10        # development cases drawn the same way from dev user tasks
OUT = Path(__file__).with_name("cases.json")


class _Probe(BaseAttack):
    """Only used for get_injection_candidates: the vectors the agent reads when doing the user task correctly."""
    name = "probe"


def _spread(pairs, n, rng, inj_ids):
    """Draw n (user, injection) pairs, cycling over injection tasks so each goal is used about equally."""
    by_inj = {i: [p for p in pairs if p[1] == i] for i in inj_ids}
    for v in by_inj.values():
        rng.shuffle(v)
    order = list(inj_ids)
    rng.shuffle(order)
    out = []
    while len(out) < n and any(by_inj.values()):
        for i in order:
            if by_inj[i] and len(out) < n:
                out.append(by_inj[i].pop())
    return sorted(out, key=lambda p: (int(p[0].split("_")[-1]), int(p[1].split("_")[-1])))


def build():
    rng = random.Random(SEED)
    suites = get_suites(VERSION)
    res = {"benchmark_version": VERSION, "seed": SEED, "dev_share": DEV_SHARE, "suites": {}, "test": [], "dev": []}
    for name in sorted(suites):
        suite = suites[name]
        probe = _Probe(suite, None)
        vectors = {uid: probe.get_injection_candidates(ut) for uid, ut in suite.user_tasks.items()}
        uids = sorted(suite.user_tasks, key=lambda u: int(u.split("_")[-1]))
        iids = sorted(suite.injection_tasks, key=lambda u: int(u.split("_")[-1]))
        shuffled = uids[:]
        rng.shuffle(shuffled)
        n_dev = round(DEV_SHARE * len(uids))
        dev_u, test_u = sorted(shuffled[:n_dev]), sorted(shuffled[n_dev:])
        res["suites"][name] = {"user_tasks": len(uids), "injection_tasks": len(iids),
                               "dev_user_tasks": dev_u, "test_user_tasks": test_u}
        for split, users, n in (("test", test_u, TEST_PER_SUITE), ("dev", dev_u, DEV_PER_SUITE)):
            pairs = [(u, i) for u in users for i in iids]
            for u, i in _spread(pairs, n, rng, iids):
                res[split].append({"case_id": f"{name}/{u}/{i}", "suite": name, "user_task": u,
                                   "injection_task": i, "vectors": vectors[u]})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    res = build()
    text = json.dumps(res, indent=1) + "\n"
    if a.check:
        same = OUT.read_text(encoding="utf-8") == text
        print("cases.json reproduces" if same else "MISMATCH")
        sys.exit(0 if same else 1)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.name}: {len(res['test'])} test, {len(res['dev'])} dev cases; "
          f"sha256 {hashlib.sha256(text.encode()).hexdigest()[:16]}")
    for s, v in res["suites"].items():
        t = [c for c in res["test"] if c["suite"] == s]
        print(f"  {s}: {len(v['test_user_tasks'])} test / {len(v['dev_user_tasks'])} dev user tasks, "
              f"{len(t)} test cases over {len({c['user_task'] for c in t})} user tasks, "
              f"{len({c['injection_task'] for c in t})} goals")


if __name__ == "__main__":
    main()
