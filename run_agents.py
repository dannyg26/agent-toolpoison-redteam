"""Run the multi-step agent benchmark across the SAFEGUARDS AXIS.

Centerpiece experiment: take a modern, agent-capable open-weight model that HAS safety alignment
(e.g. openai/gpt-oss-20b) and the SAME base with its refusals removed by abliteration
(huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2), drive both through the real tool-execution
loop under matched tool-poisoning attacks, and compare VERIFIED data leaks.

Each model entry is "label=model_id" (optionally "label=model_id@revision"). Pin the HF revision
at vLLM serve time with --revision; passing it here only records it in the results.

Run (self-hosted vLLM, OpenAI-compatible):
  OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=EMPTY \
  python run_agents.py \
    --models "safeguarded=openai/gpt-oss-20b,abliterated=huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2" \
    --reasoning-toggle gptoss_effort --framing plausible --repeats 4 --include-clean

Offline sanity of the loop (no GPU/API): python test_offline.py
"""
from __future__ import annotations
import argparse
import json
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone

from llm_client import OpenAICompatClient
from agent_loop import run_episode
from scenarios_exec import attack_scenarios, clean_scenarios


def _parse_model_entry(entry: str) -> tuple[str, str, str | None]:
    label, _, rest = entry.partition("=")
    if not rest:                       # no explicit label -> derive one from the id
        rest, label = label, label.split("/")[-1]
    model, _, rev = rest.partition("@")
    return label.strip(), model.strip(), (rev.strip() or None)


def run_model(label, model, revision, base_url, api_key, toggle, temperature,
              framings, repeats, include_clean, max_steps, delay):
    client = OpenAICompatClient(model=model, base_url=base_url, api_key=api_key,
                                temperature=temperature, reasoning_toggle=toggle, revision=revision)
    rows = []
    jobs = [(fr, sc) for fr in framings for sc in attack_scenarios(fr)]
    if include_clean:
        jobs += [("clean", sc) for sc in clean_scenarios()]
    for _tag, sc in jobs:
        for reasoning in (False, True):
            for i in range(repeats):
                r = run_episode(sc, client, reasoning=reasoning, max_steps=max_steps)
                r.update({"model": model, "label": label, "revision": revision, "run": i})
                r.pop("trace", None)                     # keep result files small; summary only
                rows.append(r)
                if delay:
                    time.sleep(delay)
    return rows


def summarize(rows, label):
    print(f"\n=== {label} — verified executed-exfil rate ===")
    print(f"{'reasoning':<10}{'framing':<14}{'n':>5}{'exfil':>8}{'unauth_read':>13}{'benign':>8}")
    print("-" * 60)
    agg = defaultdict(lambda: {"n": 0, "exfil": 0, "read": 0, "benign": 0})
    for r in rows:
        fam = "plausible" if r["framing"].startswith("plausible") else r["framing"]
        k = (r["reasoning"], fam)
        a = agg[k]
        a["n"] += 1
        a["exfil"] += r["executed_exfil"]
        a["read"] += r["unauthorized_read"]
        a["benign"] += r["benign_completed"]
    for (reasoning, fam), a in sorted(agg.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        n = a["n"] or 1
        print(f"{str(reasoning):<10}{fam:<14}{a['n']:>5}{a['exfil']/n:>8.2f}"
              f"{a['read']/n:>13.2f}{a['benign']/n:>8.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True,
                    help='comma-separated "label=model_id[@revision]" entries')
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--reasoning-toggle", default="gptoss_effort",
                    choices=["gptoss_effort", "native", "qwen_softswitch", "prompt"])
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--framing", default="plausible",
                    choices=["plausible", "neutral", "blatant", "all"])
    ap.add_argument("--repeats", type=int, default=4)
    ap.add_argument("--include-clean", action="store_true", help="also run clean utility tasks")
    ap.add_argument("--max-steps", type=int, default=6)
    ap.add_argument("--delay", type=float, default=0.0, help="seconds between calls (rate limiting)")
    args = ap.parse_args()

    framings = ["plausible", "neutral", "blatant"] if args.framing == "all" else [args.framing]
    os.makedirs("results", exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    for entry in [e for e in args.models.split(",") if e.strip()]:
        label, model, revision = _parse_model_entry(entry)
        print(f"\n########## {label}: {model} (rev={revision}) ##########", flush=True)
        try:
            rows = run_model(label, model, revision, args.base_url, args.api_key,
                             args.reasoning_toggle, args.temperature, framings,
                             args.repeats, args.include_clean, args.max_steps, args.delay)
        except Exception as e:
            print(f"  SKIPPED {label}: {type(e).__name__}: {str(e)[:200]}", flush=True)
            continue
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", f"{label}_{model}")
        out = os.path.join("results", f"agent_{safe}_{ts}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"label": label, "model": model, "revision": revision,
                       "timestamp": datetime.now(timezone.utc).isoformat(),
                       "settings": {"reasoning_toggle": args.reasoning_toggle,
                                    "temperature": args.temperature, "framings": framings,
                                    "repeats": args.repeats, "max_steps": args.max_steps,
                                    "base_url": args.base_url or os.environ.get("OPENAI_BASE_URL")},
                       "rows": rows}, f, indent=2)
        summarize(rows, label)
        print(f"\nWrote {len(rows)} episodes -> {out}", flush=True)


if __name__ == "__main__":
    main()
