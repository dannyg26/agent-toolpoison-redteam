"""Offline checks for the spending guard, paired design, thinking cap and incomplete outcomes.
No RunPod requests, model downloads, paid APIs or credentials are used.
"""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness as H
import pilot_tools as P
import pod_guard as G
import select_pilot_cases as S
from test_harness import MockServer, ScriptedAttacker, ScriptedTarget
from http.server import HTTPServer
import threading
import openai


class PilotTests(unittest.TestCase):
    def test_design_and_capability_tasks(self):
        from agentdojo.task_suite.load_suites import get_suites
        data = S.build()
        self.assertEqual(data, P.load("cases_pilot.json"))
        self.assertEqual(len(data["test"]), 10)
        self.assertEqual(len({(c["suite"], c["user_task"]) for c in data["test"]}), 10)
        self.assertEqual(len({(c["suite"], c["injection_task"]) for c in data["test"]}), 10)
        self.assertFalse({(c["suite"], c["user_task"]) for c in data["test"]} &
                         {(c["suite"], c["user_task"]) for c in data["dev"]})
        suites = get_suites(H.BENCHMARK_VERSION)
        for suite, user in S.CAPABILITY_USERS:
            env = suites[suite].load_and_inject_default_environment({})
            self.assertGreaterEqual(len(suites[suite].get_user_task_by_id(user).ground_truth(env)), 2)
        config = P.load("pilot_config.json")
        self.assertEqual(10 * len(config["attacker_labels"]) * config["candidate_budget"], 60)
        self.assertEqual(config["campaigns_per_case"], 1)

    def test_budget_includes_setup(self):
        self.assertAlmostEqual(G.deadline(1000, 2.22, 3.50, 90), 6400)
        self.assertLess(G.deadline(1000, 10, 3.50, 90), 6400)
        self.assertLess(G.deadline(1000, 2.22, 3.50, 90), 7000)  # an overdue pod cannot reset its clock
        for value in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                G.deadline(1000, value, 3.5, 90)

    def test_guard_terminates_without_laptop_and_hides_key(self):
        class Clock:
            elapsed = 0.0
            def wall(self): return 1000 + self.elapsed
            def mono(self): return 50 + self.elapsed
            def sleep(self, seconds): self.elapsed += seconds
        clock, calls = Clock(), []
        def api(method, pod, key):
            calls.append((method, pod))
            return 204
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as output:
            G.monitor("pod123", "SECRET-MUST-NOT-APPEAR", 1003, Path(tmp), request=api,
                      sleep=clock.sleep, wall=clock.wall, monotonic=clock.mono)
            self.assertTrue((Path(tmp) / "STOP_REQUESTED").exists())
            self.assertNotIn("SECRET-MUST-NOT-APPEAR", output.getvalue())
            self.assertNotIn("SECRET-MUST-NOT-APPEAR", (Path(tmp) / "guard_ready.json").read_text())
        self.assertEqual(calls, [("DELETE", "pod123")])
        self.assertLessEqual(clock.elapsed, 3.01)

    def test_no_success_does_not_hide_truncated_or_missing_cases(self):
        malformed = {"malformed": True, "attacker": {"finish_reason": "stop"}}
        full = {"error": False, "candidates": [malformed.copy() for _ in range(3)]}
        self.assertEqual(P.status(full, 3), "no_observed_success")
        full["candidates"][0]["attacker"] = {"finish_reason": "length"}
        self.assertEqual(P.status(full, 3), "incomplete")
        self.assertEqual(P.status(None, 3), "incomplete")
        full["candidates"][1]["episode"] = {"security": True}
        self.assertEqual(P.status(full, 3), "success")

    def test_generation_budget_reaches_server(self):
        server = HTTPServer(("127.0.0.1", 0), MockServer)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        client = openai.OpenAI(base_url=f"http://127.0.0.1:{server.server_port}/v1", api_key="EMPTY", max_retries=0)
        try:
            MockServer.requests, MockServer.script = [], ["final"]
            H.Attacker(client, "attacker", max_tokens=4096, thinking_token_budget=1024)(
                [{"role": "user", "content": "benign test"}], 123)
            self.assertEqual(MockServer.requests[0]["thinking_token_budget"], 1024)
            self.assertEqual(MockServer.requests[0]["max_tokens"], 4096)
        finally:
            server.shutdown()

    def test_deadline_does_not_turn_unstarted_campaign_into_failure(self):
        case = P.load("cases_pilot.json")["dev"][0]
        outcome, traces = H.run_campaign(case, 0, ScriptedAttacker(), True, 3, "Gemma", ScriptedTarget,
                                         should_stop=lambda: True)
        self.assertTrue(outcome["error"])
        self.assertTrue(outcome["deadline_reached"])
        self.assertEqual(outcome["candidates"], [])
        self.assertEqual(P.status(outcome, 3), "incomplete")

    def test_changed_budget_cannot_resume_old_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = ["--split", "dev", "--condition", "adaptive", "--target-model", "fake",
                    "--target-name", "Gemma", "--target-label", "fake", "--limit", "1", "--campaigns", "1",
                    "--workers", "1", "--out", tmp, "--budget", "3"]
            self.assertEqual(H.main(args, attacker=ScriptedAttacker(), make_llm=ScriptedTarget), 0)
            with self.assertRaises(SystemExit):
                H.main(args[:-1] + ["2"], attacker=ScriptedAttacker(), make_llm=ScriptedTarget)


if __name__ == "__main__":
    unittest.main()
