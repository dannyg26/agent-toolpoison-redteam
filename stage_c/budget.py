"""Offline proposal arithmetic, not a live RunPod quote or a spending controller."""

import json
from decimal import Decimal
from pathlib import Path


def money(value):
    number = Decimal(str(value))
    if not number.is_finite() or number < 0:
        raise ValueError("Money must be finite and nonnegative")
    return number


def calculate(config):
    for key in ("test_tasks", "conditions", "task_seconds", "development_tasks",
                "development_task_seconds", "setup_and_model_load_minutes",
                "total_environment_reset_minutes", "archive_and_termination_minutes",
                "hard_session_minutes"):
        if isinstance(config[key], bool) or not isinstance(config[key], int) or config[key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    if config.get("paid_challenge_host_allowed") is not False:
        raise ValueError("This budget assumes a free challenge host")
    hourly = money(config["maximum_hourly_usd_including_disk"])
    reserve = money(config["delayed_charge_reserve_usd"])
    settled = money(config["phase_settled_spend_usd"])
    ceiling = money(config["phase_ceiling_usd"])
    test_minutes = (Decimal(config["test_tasks"] * config["conditions"] *
                            config["task_seconds"]) / 60)
    development_minutes = (Decimal(config["development_tasks"] * config["conditions"] *
                                   config["development_task_seconds"]) / 60)
    overhead_minutes = sum(config[key] for key in ("setup_and_model_load_minutes",
                           "total_environment_reset_minutes", "archive_and_termination_minutes"))
    planned_minutes = test_minutes + development_minutes + overhead_minutes
    planned_additional = planned_minutes * hourly / 60 + reserve
    capped_additional = Decimal(config["hard_session_minutes"]) * hourly / 60 + reserve
    if planned_minutes > config["hard_session_minutes"]:
        raise ValueError("Planned schedule exceeds the session limit")
    if settled + capped_additional > ceiling:
        raise ValueError("Session cap exceeds the remaining phase budget")
    return {
        "basis": "planning limits, not measured CTF throughput or a live quote",
        "planned_session_minutes": str(planned_minutes),
        "planned_additional_usd_including_reserve": str(planned_additional),
        "capped_additional_usd_including_reserve": str(capped_additional),
        "phase_total_at_cap_usd": str(settled + capped_additional),
        "phase_remaining_after_cap_usd": str(ceiling - settled - capped_additional),
        "requires_free_challenge_host": True,
    }


if __name__ == "__main__":
    config = json.loads((Path(__file__).resolve().parent / "study_config.json").read_text())
    print(json.dumps(calculate(config), indent=2))
