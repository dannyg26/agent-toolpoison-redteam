"""Framing follow-up: configuration, cost worksheet, design comparison, freeze/check. No model calls.

    python stage_b/followup_tools.py cost       # worksheet for the chosen design + checks against the cap
    python stage_b/followup_tools.py designs    # normal / conservative cost of alternative case counts
    python stage_b/followup_tools.py plan
    python stage_b/followup_tools.py freeze | check
Outcome classification is the completed study's frozen heldout_tools.status (imported, unchanged).
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import heldout_tools as HT  # noqa: E402  (records, status, candidate_state, sha: unchanged, frozen)

CONFIG = "followup_config.json"
FILES = ["followup_config.json", "cases_followup.json", "followup_prompts.py", "followup_runtime.py",
         "followup_tools.py", "analyze_followup.py", "run_followup.sh", "select_followup_cases.py",
         "bootstrap_followup.py", "launch_followup.py", "test_followup.py", "FOLLOWUP-PROTOCOL.md",
         "audit_refusals.py", "REFUSAL-AUDIT-RULE.md",
         # unchanged dependencies shipped to the pod
         "harness.py", "heldout_runtime.py", "heldout_tools.py", "heldout_config.json", "pod_guard.py",
         "analyze_heldout.py",
         "launch_pilot.py", "pilot_tools.py", "pilot_config.json", "pilot_models.json", "test_harness.py",
         "cases.json", "cases_pilot.json", "cases_heldout.json", "select_cases.py"]


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def load_config(path=None):
    path = Path(path) if path else HERE / CONFIG
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("study") != "followup" or path.name != CONFIG:
        raise SystemExit(f"refusing non-follow-up configuration: {path.name}")
    return config


def worksheet(config, n_cases=None):
    cm = config["cost_model"]
    m, s, k = cm["measured_minutes"], cm["measured_seconds_per_candidate_4_workers"], cm["conservative_multiplier"]
    n = config["test_cases"] if n_cases is None else n_cases
    conds = len(config["attacker_labels"]) * len(config["framings"])
    budget = config["candidate_budget"]

    def scenario(name, mult, per_candidate, per_campaign, reserves):
        rows = {
            "pod start to runner": m["pod_start_to_runner"] * mult,
            "setup (installs, offline tests)": m["setup_installs_and_offline_tests"] * mult,
            "cold loads (abliterated, Gemma, aligned)": (m["cold_load_abliterated"] + m["cold_load_gemma"]
                                                          + m["cold_load_aligned"]) * mult,
            "server stops (2)": 2 * m["server_stop"] * mult,
            "warm reload (abliterated)": m["warm_reload_attacker"] * mult,
            f"clean baseline ({n} Gemma episodes)": m["clean_baseline_32_episodes"] * n / 32 * mult,
            f"attack ({conds} conditions x {n} cases x {per_campaign:g} candidates)":
                conds * n * per_campaign * per_candidate / 60,
            "request retries and stalls (scenario allowance)": reserves[0],
            "archive, download, terminate": reserves[1],
        }
        total = sum(rows.values())
        block_attack = conds * ((n + 1) // 2) * per_campaign * per_candidate / 60
        block1 = (rows["pod start to runner"] + rows["setup (installs, offline tests)"]
                  + (m["cold_load_abliterated"] + m["cold_load_gemma"] + m["cold_load_aligned"]) * mult
                  + m["server_stop"] * mult + rows[f"clean baseline ({n} Gemma episodes)"] + block_attack)
        return {"name": name, "rows": {r: round(v, 2) for r, v in rows.items()}, "total_minutes": round(total, 1),
                "collection_minutes": round(total - rows["archive, download, terminate"], 1),
                "usd": round(total / 60 * config["hourly_usd_including_disk"], 2),
                "block1_complete_at_minutes": round(block1, 1),
                "max_candidates": conds * n * budget}

    res = cm["reserve_minutes"]
    normal = scenario("normal (measured rates, measured early stopping)", 1.0, s["mean"],
                      cm["measured_candidates_per_campaign"], (0, m["archive_download_terminate"]))
    cons = scenario("conservative (slowest measured phase x1.5, all 3 candidates, overhead x1.5, allowances)", k,
                    s["slowest_phase"] * k, budget, (res["request_retries_and_stalls"], res["transfer"]))
    cap = config["maximum_session_minutes"]
    cap_usd = round(min(cap / 60 * config["hourly_usd_including_disk"], config["maximum_compute_usd"]), 4)
    soft = config["soft_stop_seconds_before_deadline"] / 60
    cutoff = cap - soft
    kill = (config["supervisor_grace_seconds"] + config["supervisor_term_wait_seconds"]) / 60
    worst = round(cap_usd + config["delayed_charge_allowance_usd"], 2)
    remaining = round(config["phase_ceiling_usd"] - config["phase_settled_spend_usd"], 4)
    checks = {
        "cap_minutes": cap, "cap_usd_at_quoted_rate": cap_usd,
        "deadline_from_config_minutes": round(min(cap, config["maximum_compute_usd"]
                                                  / config["hourly_usd_including_disk"] * 60), 2),
        "collection_cutoff_minutes": cutoff,
        "conservative_fits_with_margin": cons["collection_minutes"] + cm["required_margin_minutes"] <= cutoff,
        "conservative_margin_minutes": round(cutoff - cons["collection_minutes"], 1),
        "transfer_and_kill_within_soft_window": res["transfer"] + kill <= soft,
        "configured_total_usd_if_termination_succeeds": worst,
        "phase_remaining_usd": remaining,
        "within_phase_remaining": worst <= remaining,
        "phase_reserve_after_worst_case_usd": round(remaining - worst, 2),
        "block1_complete_before_cutoff_conservative": cons["block1_complete_at_minutes"] <= cutoff,
    }
    return [normal, cons], checks


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["cost", "designs", "plan", "freeze", "check"])
    args = ap.parse_args()
    config = load_config()
    if args.action == "cost":
        scen, checks = worksheet(config)
        for sc in scen:
            print(f"\n{sc['name']}")
            for r, v in sc["rows"].items():
                print(f"  {r:<66s} {v:7.2f} min")
            print(f"  {'TOTAL':<66s} {sc['total_minutes']:7.1f} min = ${sc['usd']:.2f}; block 1 complete at "
                  f"{sc['block1_complete_at_minutes']} min; max candidates {sc['max_candidates']}")
        print("\nchecks:", json.dumps(checks, indent=1))
        if not all(checks[k] for k in ("conservative_fits_with_margin", "transfer_and_kill_within_soft_window",
                                       "within_phase_remaining")):
            raise SystemExit("FAILED: the plan does not fit the cap and the phase budget conservatively")
    elif args.action == "designs":
        for n in (12, 16, 23, 31):
            (nor, con), _ = worksheet(config, n)
            print(f"{n:>3} cases: normal {nor['total_minutes']:6.1f} min ${nor['usd']:.2f} | conservative "
                  f"{con['total_minutes']:6.1f} min ${con['usd']:.2f} | max candidates {con['max_candidates']}")
    elif args.action == "plan":
        n, b = config["test_cases"], config["candidate_budget"]
        print(json.dumps({"cases": n, "conditions": ["abliterated+authorized", "abliterated+neutral",
                                                       "aligned+authorized", "aligned+neutral"],
                          "campaigns": 4 * n, "max_attacker_generations": 4 * n * b,
                          "max_attacked_target_episodes": 4 * n * b, "clean_episodes": n,
                          "target_compatibility_episodes": 2, "capability_episodes": 0,
                          "hard_cap_minutes_from_pod_creation": config["maximum_session_minutes"],
                          "paid_calls_made": 0}, indent=1))
    elif args.action == "freeze":
        data = {"prepared_utc": datetime.now(timezone.utc).isoformat(),
                "note": "local snapshot; commit and push before collection for an external timestamp",
                "files": {f: HT.sha(HERE / f) for f in FILES}}
        (HERE / "followup_freeze.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print("prepared follow-up freeze; no model calls")
    else:
        data = load("followup_freeze.json")
        bad = [f for f, d in data["files"].items() if HT.sha(HERE / f) != d] + sorted(set(FILES) - set(data["files"]))
        if bad:
            raise SystemExit(f"files differ from follow-up freeze: {bad}")
        print("follow-up freeze matches; no model calls")


if __name__ == "__main__":
    main()
