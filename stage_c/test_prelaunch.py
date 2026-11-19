"""Offline checks for the proposal inventory and financial limits, not agent tests."""

import copy
import json
import unittest
from decimal import Decimal
from pathlib import Path

from budget import calculate
from prepare_manifest import parse_tasks

ROOT = Path(__file__).resolve().parent


class BudgetChecks(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "study_config.json").read_text())

    def test_current_budget(self):
        result = calculate(self.config)
        self.assertEqual(Decimal(result["planned_session_minutes"]), Decimal("161"))
        self.assertEqual(Decimal(result["capped_additional_usd_including_reserve"]), Decimal("6.76"))
        # 2.0675 settled + 0.10 failed lease 1 (upper estimate) + 6.76 cap for lease 2.
        self.assertEqual(Decimal(result["phase_total_at_cap_usd"]), Decimal("8.9275"))

    def test_rate_increase_fails(self):
        self.config["maximum_hourly_usd_including_disk"] = "3.00"
        with self.assertRaises(ValueError):
            calculate(self.config)

    def test_longer_task_budget_fails(self):
        self.config["task_seconds"] = 360
        with self.assertRaises(ValueError):
            calculate(self.config)

    def test_repeated_session_does_not_reset_budget(self):
        self.config["phase_settled_spend_usd"] = "8.8275"
        with self.assertRaises(ValueError):
            calculate(self.config)

    def test_invalid_money(self):
        for value in ("NaN", "Infinity", "-1"):
            config = copy.deepcopy(self.config)
            config["maximum_hourly_usd_including_disk"] = value
            with self.assertRaises(ValueError):
                calculate(config)

    def test_paid_host_requires_new_budget(self):
        self.config["paid_challenge_host_allowed"] = True
        with self.assertRaises(ValueError):
            calculate(self.config)


class InventoryChecks(unittest.TestCase):
    def test_full_category_selection(self):
        manifest = json.loads((ROOT / "challenge_manifest.json").read_text())
        self.assertEqual(manifest["selected_tasks"], 14)
        self.assertEqual(manifest["category_counts"], {"pwn": 11, "web": 3})
        self.assertEqual(len({task["id"] for task in manifest["tasks"]}), 14)
        self.assertIn("Hard", manifest["difficulty_counts"])
        for task in manifest["tasks"]:
            self.assertNotIn("flag", task)
            self.assertNotIn("solution", task)

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            parse_tasks("| web | 2023q | example | Easy |\n" * 2)

    def test_automatic_launch_disabled(self):
        config = json.loads((ROOT / "study_config.json").read_text())
        self.assertIs(config["automatic_launch_enabled"], False)
        # Live calls may be enabled only in a configuration covered by the final collection freeze.
        if config["allow_live_model_calls"]:
            freeze = json.loads((ROOT / "ctf_freeze.json").read_text())
            self.assertIs(freeze["externally_timestamped_before_collection"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
