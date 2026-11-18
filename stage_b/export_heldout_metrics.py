"""Write the PUBLIC aggregate record of the held-out run: no attack text, no transcripts, no model outputs.

Added after collection (reporting only). It re-runs the frozen analysis (analyze_heldout.report) on the private
download, audits the recorded settings against heldout_config.json, totals usage, and records file hashes.

    python stage_b/export_heldout_metrics.py --download <private>/download --run-dir <private> \
        --balance-before 13.0648 --balance-after 11.126 --output stage_b/heldout_observed_metrics.json
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_heldout as A  # noqa: E402
import heldout_tools as T  # noqa: E402

RESULT_FILES = ["baselines/test__fixed__none__gemma.jsonl", "baselines/test__no_attack__none__gemma.jsonl",
                "capability_abliterated/dev__no_attack__none__abliterated.jsonl",
                "capability_aligned/dev__no_attack__none__aligned.jsonl",
                "runs_block1/test__adaptive__abliterated__gemma.jsonl", "runs_block1/test__adaptive__aligned__gemma.jsonl",
                "runs_block2/test__adaptive__abliterated__gemma.jsonl", "runs_block2/test__adaptive__aligned__gemma.jsonl",
                "target_compatibility/dev__no_attack__none__gemma.jsonl"]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(download, config):
    expected = {"workers": config["workers"], "request_timeout": config["request_timeout_seconds"],
                "attacker_max_tokens": config["attacker_max_tokens"], "target_max_tokens": config["target_max_tokens"],
                "budget": config["candidate_budget"], "campaigns": 1, "max_error_rate": config["harness_max_error_rate"],
                "attacker_thinking_budget": config["attacker_thinking_budget"]}
    mismatches, usage = [], {"agent_episodes": 0, "target_llm_calls": 0, "target_prompt_tokens": 0,
                             "target_completion_tokens": 0, "attacker_generations": 0,
                             "attacker_prompt_tokens": 0, "attacker_completion_tokens": 0, "error_records": 0}
    for rel in RESULT_FILES:
        rows = T.records(Path(download) / rel)
        think = config["capability_thinking_budget"] if rel.startswith("capability") else config["target_thinking_budget"]
        for r in rows:
            s = r.get("settings", {})
            for k, v in {**expected, "target_thinking_budget": think}.items():
                if s.get(k) != v:
                    mismatches.append({"file": rel, "setting": k, "recorded": s.get(k), "expected": v})
            usage["error_records"] += bool(r.get("error") is True or r.get("exception"))
            eps = [r["episode"]] if r.get("episode") else [c["episode"] for c in r.get("candidates", []) if c.get("episode")]
            for e in eps:
                usage["agent_episodes"] += 1
                usage["target_llm_calls"] += e["target_calls"]
                usage["target_prompt_tokens"] += e["prompt_tokens"]
                usage["target_completion_tokens"] += e["completion_tokens"]
            for c in r.get("candidates", []):
                a = c.get("attacker", {})
                usage["attacker_generations"] += 1
                usage["attacker_prompt_tokens"] += a.get("prompt_tokens") or 0
                usage["attacker_completion_tokens"] += a.get("completion_tokens") or 0
    return mismatches, usage


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--download", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--balance-before", type=float, required=True)
    ap.add_argument("--balance-after", type=float, required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    download, run = Path(args.download), Path(args.run_dir)
    config = T.load_config()
    report = A.report(download)
    pod_report = json.loads((download / "heldout_summary.json").read_text(encoding="utf-8"))
    mismatches, usage = audit(download, config)
    status = json.loads((run / "run_status.json").read_text(encoding="utf-8"))
    pod = json.loads((run / "pod.json").read_text(encoding="utf-8"))
    out = {
        "scope": "held-out AgentDojo comparison, frozen procedure; aggregate outcomes only (no attack text)",
        "reporting_utility_added_after_collection": True,
        "frozen_commit": "6130230181998a895019bada454c0ba49a09ff66",
        "analysis": "unchanged analyze_heldout.report",
        "report_rederived_equals_pod_report": report == pod_report,
        "settings_audit_mismatches": mismatches,
        "pod_freeze_equals_repo_freeze": json.loads((download / "heldout_freeze.json").read_text(encoding="utf-8"))
                                          == T.load("heldout_freeze.json"),
        "run": {"pod_id": status["pod_id"], "created_at": pod.get("createdAt"), "terminated": status["terminated"],
                "final_archive_verified": status["final_archive_verified"],
                "elapsed_minutes_creation_to_termination": status["elapsed_minutes"],
                "controller_quoted_spend_usd": status["maximum_quoted_spend_before_tax"],
                "balance_before_usd": args.balance_before, "balance_after_usd": args.balance_after,
                "measured_credit_decrease_usd": round(args.balance_before - args.balance_after, 4),
                "hard_cap_minutes": config["maximum_session_minutes"],
                "gpu": (download / "gpu.txt").read_text(encoding="utf-8").strip(),
                "archive_sha256": (download / "archive.sha256").read_text(encoding="utf-8").strip()},
        "usage": usage,
        "primary": report["primary"], "blocks": report["blocks"], "per_case": report["per_case"],
        "secondary_descriptive": report["secondary_descriptive"], "capability": report["capability"],
        "file_diagnostics": report["file_diagnostics"], "supervisor_events": report["supervisor_events"],
        "source_sha256": {rel: sha256(download / rel) for rel in RESULT_FILES},
    }
    Path(args.output).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {args.output}: verdict: {report['primary']['verdict']}; audit mismatches {len(mismatches)}; "
          f"re-derived equals pod report: {out['report_rederived_equals_pod_report']}")


if __name__ == "__main__":
    main()
