"""LLM client for driving modern, agent-capable models through a multi-step tool loop.

One interface over any OpenAI-compatible endpoint (self-hosted vLLM/SGLang, Ollama, OpenAI,
OpenRouter), plus a deterministic ScriptedClient for running the whole pipeline offline with no
GPU or API key.

The agent emits one JSON tool call per step: {"tool": "<name>", "args": {...}}. A `reasoning`
flag toggles the model's step-by-step thinking so we can compare reasoning ON vs OFF on the SAME
weights. Different model families expose that switch differently, hence `reasoning_toggle`.
"""
from __future__ import annotations
import json
import os
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Turn:
    text: str = ""            # assistant content (should contain the JSON tool call)
    reasoning: str = ""       # chain-of-thought, when the backend exposes it separately
    finish_reason: str = ""   # "stop" / "length" (=> truncated) / ...


@dataclass
class ToolTurn:
    """One assistant turn in NATIVE tool-calling mode."""
    assistant_message: dict               # raw assistant message to echo back (holds tool_calls)
    tool_calls: list = field(default_factory=list)   # [{"id","name","args"}]
    content: str = ""
    reasoning: str = ""
    finish_reason: str = ""


def extract_json_call(text: str) -> tuple[str | None, dict]:
    """Pull the last {"tool": ...} JSON object out of free-form model text.

    Uses a brace-balanced scan (raw_decode) so nested objects like
    {"tool": "x", "args": {"path": "..."}} parse correctly.
    """
    dec = json.JSONDecoder()
    found: tuple[str | None, dict] | None = None
    idx = 0
    while True:
        start = text.find("{", idx)
        if start == -1:
            break
        try:
            obj, end = dec.raw_decode(text, start)
            if isinstance(obj, dict) and "tool" in obj:
                found = (obj.get("tool"), obj.get("args", {}) or {})
            idx = end
        except json.JSONDecodeError:
            idx = start + 1
    return found if found else (None, {})


class OpenAICompatClient:
    """Any OpenAI-compatible /chat/completions endpoint.

    Local vLLM:  base_url="http://localhost:8000/v1", api_key="EMPTY"
    Ollama:      base_url="http://localhost:11434/v1", api_key="ollama"
    """

    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None,
                 temperature: float = 0.7, reasoning_toggle: str = "gptoss_effort",
                 max_tokens: int = 4096, revision: str | None = None):
        """reasoning_toggle:
        - "gptoss_effort": OpenAI gpt-oss models (and their abliterated variants). gpt-oss is
          reasoning-native (harmony format) and has NO true "off"; we map OFF -> "low" effort,
          ON -> "high" via the chat template's reasoning_effort. CAVEAT for the paper: the gpt-oss
          on/off contrast is low-vs-high reasoning effort, not CoT present/absent.
        - "native": Qwen3-style enable_thinking (same weights, reasoning on/off).
        - "qwen_softswitch": Qwen3 /think | /no_think appended to the user message.
        - "prompt": elicit CoT via a system-prompt instruction (works on any model; a different
          claim: does *eliciting* CoT change behavior).

        revision: the exact Hugging Face commit of the served weights. NOT sent over the API
        (vLLM pins it at serve time via --revision); stored only so the runner records it.
        """
        from openai import OpenAI  # lazy import so ScriptedClient needs no dependency
        self.model = model
        self.temperature = temperature
        self.reasoning_toggle = reasoning_toggle
        self.max_tokens = max_tokens
        self.revision = revision
        resolved_base = base_url or os.environ.get("OPENAI_BASE_URL") or ""
        self.is_openrouter = "openrouter" in resolved_base
        self.client = OpenAI(base_url=resolved_base or None,
                             api_key=api_key or os.environ.get("OPENAI_API_KEY", "EMPTY"))

    # ---- reasoning-toggle plumbing shared by every call ----
    def _prep(self, messages: list[dict], reasoning: bool) -> tuple[list[dict], dict]:
        msgs = [dict(m) for m in messages]
        extra_body: dict = {}
        if self.is_openrouter:
            extra_body["provider"] = {"sort": "throughput", "allow_fallbacks": True}
        if self.reasoning_toggle == "gptoss_effort":
            extra_body["chat_template_kwargs"] = {"reasoning_effort": "high" if reasoning else "low"}
        elif self.reasoning_toggle == "native":
            extra_body["chat_template_kwargs"] = {"enable_thinking": reasoning}
        elif self.reasoning_toggle == "qwen_softswitch":
            for m in reversed(msgs):
                if m["role"] == "user":
                    m["content"] = f"{m['content']} {'/think' if reasoning else '/no_think'}"
                    break
        elif self.reasoning_toggle == "prompt" and reasoning:
            if msgs and msgs[0]["role"] == "system":
                msgs[0]["content"] += ("\n\nThink step by step about each tool before acting, then "
                                       "give your JSON decision.")
        return msgs, extra_body

    def _create_with_retry(self, messages, extra_body, tools=None, max_retries=6):
        from openai import APIError, APIConnectionError, RateLimitError
        kw = dict(model=self.model, temperature=self.temperature, max_tokens=self.max_tokens,
                  messages=messages, extra_body=extra_body or None)
        if tools:
            kw["tools"] = tools
            kw["tool_choice"] = "auto"
        delay = 4.0
        for attempt in range(max_retries):
            try:
                return self.client.chat.completions.create(**kw)
            except (RateLimitError, APIConnectionError):
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay * (2 ** attempt) + random.uniform(0, 2))
            except APIError as e:
                if getattr(e, "status_code", None) == 429 and attempt < max_retries - 1:
                    time.sleep(delay * (2 ** attempt) + random.uniform(0, 2))
                else:
                    raise

    def chat(self, messages: list[dict], reasoning: bool) -> Turn:
        msgs, extra_body = self._prep(messages, reasoning)
        resp = self._create_with_retry(msgs, extra_body)
        msg = resp.choices[0].message
        text = msg.content or ""
        cot = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None) or ""
        if not cot:
            for tag in ("think", "reasoning"):
                m = re.search(rf"<{tag}>(.*?)</{tag}>", text, flags=re.S)
                if m:
                    cot = m.group(1).strip()
                    break
        finish = getattr(resp.choices[0], "finish_reason", "") or ""
        return Turn(text=text, reasoning=cot, finish_reason=finish)

    def chat_tools(self, messages: list[dict], tools: list, reasoning: bool) -> ToolTurn:
        """NATIVE tool-calling: pass real tool schemas, read structured tool_calls back."""
        msgs, extra_body = self._prep(messages, reasoning)
        resp = self._create_with_retry(msgs, extra_body, tools=tools)
        msg = resp.choices[0].message
        calls = []
        for tc in (getattr(msg, "tool_calls", None) or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except (json.JSONDecodeError, TypeError):
                args = {}
            calls.append({"id": tc.id, "name": tc.function.name, "args": args})
        cot = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None) or ""
        # Echo a CLEAN assistant message (role/content/tool_calls only) — do not send the reasoning
        # channel back, which some servers reject on input.
        am: dict = {"role": "assistant"}
        if msg.content:
            am["content"] = msg.content
        if getattr(msg, "tool_calls", None):
            am["tool_calls"] = [{"id": tc.id, "type": "function",
                                 "function": {"name": tc.function.name,
                                              "arguments": tc.function.arguments or "{}"}}
                                for tc in msg.tool_calls]
        finish = getattr(resp.choices[0], "finish_reason", "") or ""
        return ToolTurn(assistant_message=am, tool_calls=calls, content=msg.content or "",
                        reasoning=cot, finish_reason=finish)


class ScriptedClient:
    """Deterministic, no-dependency stand-in for offline tests. NOT a model.

    Replays a fixed list of (tool, args) steps regardless of context. Lets us exercise the full
    multi-step loop + sandbox + verified-outcome checks without a GPU or API key.
    """

    def __init__(self, script: list[tuple[str, dict]], reasoning_toggle: str = "scripted"):
        self.script = script
        self.reasoning_toggle = reasoning_toggle
        self._i = 0

    def chat(self, messages: list[dict], reasoning: bool) -> Turn:
        tool, args = self.script[self._i] if self._i < len(self.script) else ("finish", {})
        self._i += 1
        return Turn(text=json.dumps({"tool": tool, "args": args}), finish_reason="stop")

    def chat_tools(self, messages: list[dict], tools: list, reasoning: bool) -> ToolTurn:
        name, args = self.script[self._i] if self._i < len(self.script) else ("finish", {})
        self._i += 1
        tcid = f"call_{self._i}"
        am = {"role": "assistant", "content": None,
              "tool_calls": [{"id": tcid, "type": "function",
                              "function": {"name": name, "arguments": json.dumps(args)}}]}
        return ToolTurn(assistant_message=am, tool_calls=[{"id": tcid, "name": name, "args": args}],
                        finish_reason="tool_calls")
