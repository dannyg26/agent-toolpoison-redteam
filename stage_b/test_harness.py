"""Offline tests for stage_b/harness.py. No GPU, no network: scripted models and a local mock server.

    python stage_b/test_harness.py

1. Every injection vector accepts awkward text (quotes, colons, YAML markers, braces, newlines).
2. A scripted target that follows the user task's ground truth, and obeys an injection only when it contains the
   marker OBEY-<injection id>, gives: no success on plain text, success on the marker, encountered detection,
   early stopping, malformed candidates, adaptive vs non-adaptive feedback, and the runner's resume.
3. TargetLLM against a mock OpenAI-compatible server: role "system" (not "developer"), temperature 0 is sent,
   tools are sent, tool results carry their call id, and bad JSON arguments / context overflow end the turn.
"""
import json, re, shutil, sys, tempfile, threading, warnings
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent))
import openai
import harness as H
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.functions_runtime import FunctionCall
from agentdojo.task_suite.load_suites import get_suites
from agentdojo.types import ChatAssistantMessage, get_text_content_as_str, text_content_block_from_string

SUITES = get_suites(H.BENCHMARK_VERSION)
CASES = json.loads((Path(__file__).parent / "cases.json").read_text(encoding="utf-8"))


def suite_for_env(env):
    return next(s for s in SUITES.values() if isinstance(env, s.environment_type))


class ScriptedTarget(BasePipelineElement):
    """Turn 1: the user task's ground-truth calls. If a tool result contains OBEY-<id>: that injection task's
    ground-truth calls. Then the user task's ground-truth answer."""

    def __init__(self):
        self.stats = H.EpisodeStats()
        self.name = "scripted"
        self.n = 0

    def query(self, query, runtime, env=None, messages=[], extra_args={}):
        suite = suite_for_env(env)
        ut = next(t for t in suite.user_tasks.values() if t.PROMPT == query)
        assistant = [m for m in messages if m["role"] == "assistant"]
        tool_text = " ".join(get_text_content_as_str(m["content"] or []) for m in messages if m["role"] == "tool")
        obeyed = any(m.get("_obey") for m in assistant)
        hit = re.search(r"OBEY-(injection_task_\d+)", tool_text)
        self.stats.calls += 1
        inj = suite.get_injection_task_by_id(hit.group(1)) if hit else None
        answer = getattr(ut, "GROUND_TRUTH_OUTPUT", "") or "Done."
        if inj is not None:          # some injection goals are met by what the agent SAYS, not by a tool call
            answer = (getattr(inj, "GROUND_TRUTH_OUTPUT", "") or "") + "\n" + answer
        if not assistant:
            msg = self._calls(ut.ground_truth(env))
        elif inj is not None and not obeyed and inj.ground_truth(env):
            msg = self._calls(inj.ground_truth(env))
            msg["_obey"] = True
        else:
            msg = ChatAssistantMessage(role="assistant", tool_calls=None,
                                       content=[text_content_block_from_string(answer)])
        return query, runtime, env, [*messages, msg], extra_args

    def _calls(self, calls):
        out = []
        for c in calls:
            self.n += 1
            out.append(FunctionCall(function=c.function, args=c.args, id=f"call_{self.n}"))
        return ChatAssistantMessage(role="assistant", content=[text_content_block_from_string("")], tool_calls=out)


class ScriptedAttacker:
    """Attempt 1: harmless text. Attempt 2: a refusal with no tags. Attempt 3+: the marker."""

    def __init__(self):
        self.seen = []

    def __call__(self, messages, seed):
        self.seen.append([dict(m) for m in messages])
        k = sum(1 for m in messages if m["role"] == "assistant") + 1
        goal = re.search(r'Attacker goal:\n"""(.*?)"""', messages[1]["content"], re.S).group(1)
        inj_id = next(i for s in SUITES.values() for i, t in s.injection_tasks.items() if t.GOAL == goal)
        content = {1: "<injection>Reminder: the office is closed on Friday.</injection>",
                   2: "I can't help with that."}.get(k, f"Thinking...\n<injection>OBEY-{inj_id} now</injection>")
        return {"content": content, "reasoning": None, "finish_reason": "stop", "prompt_tokens": 1,
                "completion_tokens": 1, "seconds": 0.0}


def test_vectors_accept_awkward_text():
    text = 'Line one: "quoted" and \'single\'\n- dash item\n# hash {braces} [brackets] & *star* | pipe >gt\n\ttab'
    n = 0
    for suite in SUITES.values():
        for v in suite.get_injection_vector_defaults():
            env = H.injected_environment(suite, {v: text})
            dump = json.dumps(env.model_dump(mode="json"), ensure_ascii=False)
            assert json.dumps(text, ensure_ascii=False)[1:-1] in dump, (suite.name, v)   # exact text, newlines kept
            assert "ZZINJ" not in dump
            n += 1
        plain = {v: "plain words only" for v in suite.get_injection_vector_defaults()}   # same as the official path
        assert (H.injected_environment(suite, plain).model_dump(mode="json")
                == suite.load_and_inject_default_environment(plain).model_dump(mode="json")), suite.name
    print(f"ok  vectors take awkward text exactly; plain text matches AgentDojo's loader ({n} vectors)")


def test_campaigns():
    cases = CASES["dev"][::4]                     # 10 dev cases, all four suites
    for case in cases:
        for adaptive in (True, False):
            att = ScriptedAttacker()
            out, traces = H.run_campaign(case, 0, att, adaptive, 5, "Qwen", ScriptedTarget)
            c = out["candidates"]
            assert out["success_at"] == 3 and len(c) == 3 and not out["error"], (case["case_id"], out["success_at"])
            assert c[0]["episode"]["security"] is False and c[0]["episode"]["encountered"] is True, case["case_id"]
            assert c[1]["malformed"] and "episode" not in c[1]
            assert c[2]["episode"]["security"] is True
            conv = out["attacker_conversation"]
            fb = conv[3]["content"]
            assert ("did not achieve the goal" in fb) == adaptive, fb
            assert "contained no text between" in conv[5]["content"]
            assert "Tool calls the assistant made" not in " ".join(
                m["content"] for m in conv if m["role"] == "user") or adaptive
    print(f"ok  campaigns: success at attempt 3, malformed attempt skipped, feedback only when adaptive "
          f"({len(cases)} cases x 2)")


def test_runner_and_resume():
    tmp = Path(tempfile.mkdtemp())
    try:
        base = ["--split", "dev", "--target-model", "x", "--target-name", "Qwen", "--target-label", "t",
                "--out", str(tmp), "--limit", "6", "--workers", "4"]
        assert H.main(base + ["--condition", "no_attack"], make_llm=ScriptedTarget) == 0
        na = [json.loads(l) for l in (tmp / "dev__no_attack__none__t.jsonl").read_text().splitlines()]
        assert na and all(r["episode"]["utility"] is not None for r in na)
        assert H.main(base + ["--condition", "fixed"], make_llm=ScriptedTarget) == 0
        fx = [json.loads(l) for l in (tmp / "dev__fixed__none__t.jsonl").read_text().splitlines()]
        assert len(fx) == 6 and all(r["episode"]["security"] is False for r in fx)
        assert all("Emma Johnson" in r["injection"] and "Qwen" in r["injection"] for r in fx)
        args = base + ["--condition", "adaptive", "--attacker-label", "a", "--campaigns", "2"]
        assert H.main(args, attacker=ScriptedAttacker(), make_llm=ScriptedTarget) == 0
        p = tmp / "dev__adaptive__a__t.jsonl"
        ad = [json.loads(l) for l in p.read_text().splitlines()]
        assert len(ad) == 12 and all(r["success_at"] == 3 for r in ad)
        assert H.main(args, attacker=ScriptedAttacker(), make_llm=ScriptedTarget) == 0
        assert len(p.read_text().splitlines()) == 12, "resume re-ran finished units"
        seeds = {r["key"]: r["seed"] for r in ad}
        assert len(set(seeds.values())) == 12
        print(f"ok  runner: no_attack {len(na)}, fixed {len(fx)}, adaptive {len(ad)} campaigns; resume skips done; "
              f"seeds distinct")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class MockServer(BaseHTTPRequestHandler):
    script = []
    requests = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        MockServer.requests.append(body)
        kind = MockServer.script.pop(0)
        if kind == "too_long":
            self.send_response(400)
            payload = {"error": {"message": "maximum context length is 32768 tokens", "type": "BadRequestError"}}
        else:
            self.send_response(200)
            msg = {"role": "assistant", "content": None}
            if kind == "call":
                msg["tool_calls"] = [{"id": "chatcmpl-tool-1", "type": "function", "function": {
                    "name": "get_most_recent_transactions", "arguments": json.dumps({"n": 100})}}]
            elif kind == "bad_args":
                msg["tool_calls"] = [{"id": "chatcmpl-tool-2", "type": "function", "function": {
                    "name": "get_balance", "arguments": "{not json"}}]
            else:
                msg["content"] = "All done."
            msg["reasoning_content"] = "thinking..."
            payload = {"id": "x", "object": "chat.completion", "created": 0, "model": body["model"],
                       "choices": [{"index": 0, "message": msg, "finish_reason": "stop"}],
                       "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}
        data = json.dumps(payload).encode()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def test_target_adapter():
    srv = HTTPServer(("127.0.0.1", 0), MockServer)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    client = openai.OpenAI(base_url=f"http://127.0.0.1:{srv.server_port}/v1", api_key="EMPTY", max_retries=0)
    suite = SUITES["banking"]
    try:
        MockServer.script, MockServer.requests = ["call", "final"], []
        ep, tr = H.run_episode(suite, "user_task_0", None, {}, lambda: H.TargetLLM(client, "tgt"))
        r0, r1 = MockServer.requests
        assert r0["messages"][0]["role"] == "system", r0["messages"][0]["role"]
        assert r0["temperature"] == 0.0 and r0["tools"] and r0["tool_choice"] == "auto"
        tool_msg = next(m for m in r1["messages"] if m["role"] == "tool")
        assert tool_msg["tool_call_id"] == "chatcmpl-tool-1"
        assert ep["target_calls"] == 2 and ep["tool_calls"][0]["function"] == "get_most_recent_transactions"
        assert ep["prompt_tokens"] == 20 and tr["target_reasoning"] == ["thinking...", "thinking..."]
        assert ep["error"] is None and ep["utility"] is not None

        MockServer.script = ["bad_args"]
        ep, _ = H.run_episode(suite, "user_task_0", None, {}, lambda: H.TargetLLM(client, "tgt"))
        assert ep["bad_tool_args"] == 1 and ep["error"] is None and ep["tool_calls"] == []

        MockServer.script = ["call", "too_long"]
        ep, _ = H.run_episode(suite, "user_task_0", None, {}, lambda: H.TargetLLM(client, "tgt"))
        assert ep["context_exceeded"] == 1 and ep["error"] is None
        print("ok  target adapter: system role, temperature 0 sent, tool ids, bad arguments and overflow end the turn")
    finally:
        srv.shutdown()


if __name__ == "__main__":
    test_vectors_accept_awkward_text()
    test_campaigns()
    test_runner_and_resume()
    test_target_adapter()
    print("ALL PASSED")
