"""Reproduce descriptive pilot counts without printing prompts or model responses.

Added after collection for reporting; the frozen pilot_tools.status rule is unchanged.
Requires the private downloaded run directory. No model calls or inference tests.
"""
import argparse
import hashlib
import json
from pathlib import Path

import pilot_tools as P


def episode_summary(episodes):
    fields = ("target_calls", "prompt_tokens", "completion_tokens", "truncated",
              "context_exceeded", "bad_tool_args", "tool_errors", "wall_seconds")
    return {
        "episodes": len(episodes),
        "utility_true": sum(e["utility"] is True for e in episodes),
        "security_true": sum(e["security"] is True for e in episodes),
        "errors": sum(bool(e.get("error")) for e in episodes),
        "encountered_true": sum(e.get("encountered") is True for e in episodes),
        "encountered_false": sum(e.get("encountered") is False for e in episodes),
        "tool_calls": sum(len(e["tool_calls"]) for e in episodes),
        **{k: round(sum(e.get(k, 0) or 0 for e in episodes), 6) for k in fields},
    }


def aggregate(download):
    result = {"reporting_utility_added_after_collection": True,
              "classification": "unchanged frozen pilot_tools.status",
              "arms": {}, "checks": {}, "per_case": [], "source_sha256": {}}
    by_arm = {}

    def read(relative):
        path = download / relative
        result["source_sha256"][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        return P.records(path)

    cases = P.load("cases_pilot.json")["test"]
    config = P.load("pilot_config.json")
    for arm in ("aligned", "abliterated"):
        rows = read(f"runs/test__adaptive__{arm}__gemma.jsonl")
        by_arm[arm] = {r["case_id"]: r for r in rows}
        if set(by_arm[arm]) != {c["case_id"] for c in cases}:
            raise ValueError("case inventory differs from frozen plan")
        candidates = [c for r in rows for c in r["candidates"]]
        episodes = [c["episode"] for c in candidates if c.get("episode")]
        result["arms"][arm] = {
            "campaigns": len(rows),
            "first_candidate_successes": sum(
                bool(r["candidates"]) and r["candidates"][0].get("episode", {}).get("security") is True
                for r in rows),
            "candidate_generations": len(candidates),
            "malformed_candidates": sum(c["malformed"] for c in candidates),
            "attacker_capped_candidates": sum(c["attacker"]["finish_reason"] == "length" for c in candidates),
            "attacker_prompt_tokens": sum(c["attacker"].get("prompt_tokens", 0) or 0 for c in candidates),
            "attacker_completion_tokens": sum(c["attacker"].get("completion_tokens", 0) or 0 for c in candidates),
            "target": episode_summary(episodes),
        }
    checks = {
        "clean_test": "runs/test__no_attack__none__gemma.jsonl",
        "capability_aligned": "capability_aligned/dev__no_attack__none__aligned.jsonl",
        "capability_abliterated": "capability_abliterated/dev__no_attack__none__abliterated.jsonl",
        "target_compatibility": "target_compatibility/dev__no_attack__none__gemma.jsonl",
    }
    for name, relative in checks.items():
        result["checks"][name] = episode_summary([r["episode"] for r in read(relative)])
    for case in cases:
        out = {k: case[k] for k in ("case_id", "suite", "user_task", "injection_task")}
        for arm in ("aligned", "abliterated"):
            row = by_arm[arm][case["case_id"]]
            out[arm] = {
                "status": P.status(row, config["candidate_budget"]),
                "success_at": row.get("success_at"),
                "candidates": len(row["candidates"]),
                "attacker_caps": sum(c["attacker"]["finish_reason"] == "length" for c in row["candidates"]),
                "target_caps": sum(c.get("episode", {}).get("truncated", 0) for c in row["candidates"]),
            }
        result["per_case"].append(out)
    result["frozen_summary"] = json.loads((download / "pilot_summary.json").read_text(encoding="utf-8"))
    for arm, numbers in result["frozen_summary"]["arms"].items():
        for state, count in numbers.items():
            if count != sum(c[arm]["status"] == state for c in result["per_case"]):
                raise ValueError("frozen summary and individual classifications differ")
    episode_groups = [a["target"] for a in result["arms"].values()] + list(result["checks"].values())
    result["totals_excluding_server_tool_checks"] = {
        "agent_episodes": sum(e["episodes"] for e in episode_groups),
        "llm_calls": sum(e["target_calls"] for e in episode_groups) +
                     sum(a["candidate_generations"] for a in result["arms"].values()),
        "prompt_tokens": sum(e["prompt_tokens"] for e in episode_groups) +
                         sum(a["attacker_prompt_tokens"] for a in result["arms"].values()),
        "completion_tokens": sum(e["completion_tokens"] for e in episode_groups) +
                             sum(a["attacker_completion_tokens"] for a in result["arms"].values()),
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = aggregate(args.download)
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data["totals_excluding_server_tool_checks"]))
