# Safety-removal studies on open-weight LLMs

This repository holds several studies. **The current one is the red-team attacker study**:

> **Is abliterating your red-team attacker worth it?** It compares three ways of getting a willing,
> capable attacker LLM: prompting an aligned model, abliterating it (weight surgery that removes
> refusals), and downloading a model trained for red-teaming (Jailbreak-R1). All three run against two
> targets on 150 StrongREJECT goals, labelled blind by two AI agents.
>
> - Design and status: [RED-TEAM-STUDY.md](RED-TEAM-STUDY.md)
> - Results: [RESULTS.md](RESULTS.md)
> - Pre-registered plan, deviations and corrections: [ANALYSIS-PLAN.md](ANALYSIS-PLAN.md)
> - Labelling rule: [LABELING-PROTOCOL.md](LABELING-PROTOCOL.md)
> - Code: `redteam.py` (collection), `rescore.py` + `sr_judge.py` (scoring), `estimate.py` (sampling and
>   estimates; `--selftest`), `summarize.py`, `adjudicate.py`
>
> Transcripts, scores and labels are gitignored: they contain model-generated harmful text.

The rest of this README describes the earlier tool-poisoning study.

---

## Earlier study: Do Safeguards Matter? Verified Data Leaks in Modern Tool-Using LLM Agents

A red-teaming framework that drives **modern, agent-capable open-weight models** through a
**real multi-step tool-execution loop** under MCP **tool-poisoning** attacks (a malicious
instruction hidden in a tool's description), and measures **verified data leaks** — a sensitive
secret actually reaching an attacker endpoint — not just the model's stated intent.

The headline axis is **safety alignment itself**: the same base model **with** safeguards vs. the
**same weights with refusals surgically removed by abliteration**. Crossed with a reasoning
on/off axis and matched attack framings, this isolates what safety training actually buys you once
an agent is executing tools.

## Why this design

- **Modern, agent-capable models.** Primary pair: **`unsloth/gpt-oss-20b-BF16`** (safeguarded
  baseline) vs. **`huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2`** (the SAME BF16 weights with
  safeguards removed). Both are reasoning- and tool-use-native. A 120B pair is configured too.
  *Precision matters:* the abliterated model is BF16, so we use the BF16 baseline (not the default
  MXFP4 `openai/gpt-oss-20b`) to avoid a quantization confound — same precision, only safety differs.
- **Real agents, not single decisions.** The model calls tools over several turns; the sandbox
  *executes* them and a **canary secret** either leaves to an attacker host or it doesn't.
- **Safeguards as a controlled variable.** Abliteration (Arditi et al., *Refusal in Language
  Models Is Mediated by a Single Direction*, NeurIPS 2024) removes the refusal direction while
  preserving capability — so the safeguarded/abliterated pair differs in ~one thing.
- **Confound-controlled attacks.** Each attack appears in matched **plausible / neutral / blatant**
  framings, so a justification effect is separable from plain instruction-following, and `blatant`
  is a sanity floor the model should refuse.
- **Verified harm, tightened.** Posting a *filename* is **not** a leak; only posting the canary's
  **contents** to an attacker host counts (see `test_offline.py`, case 4).

## Layout

| File | Role |
|------|------|
| `sandbox.py`        | In-memory tool sandbox with **canary** secrets; verified leak / completion checks. |
| `scenarios_exec.py` | 8 attack tasks × {plausible, neutral, blatant} + clean utility tasks. |
| `agent_loop.py`     | Multi-step agent loop; records `unauthorized_read`, `executed_exfil`, `benign_completed`. |
| `llm_client.py`     | OpenAI-compatible client (vLLM/Ollama/OpenRouter) + reasoning toggles; offline `ScriptedClient`. |
| `run_agents.py`     | Runs the **safeguards axis** across models × reasoning × framings; writes `results/`. |
| `stats_exec.py`     | Bootstrap 95% CIs: safeguards effect, reasoning effect, per-model rates. |
| `test_offline.py`   | Full-pipeline self-test — **no GPU/API** needed. |
| `setup_gpu.sh`      | One-shot vLLM + deps install for any Ubuntu + NVIDIA GPU box. |
| `RUNPOD.md`         | Cheapest path: run on a per-minute GPU host (RunPod/Vast/Lambda). |
| `SERVE.md` / `AZURE.md` | General serving notes; Azure-specific runbook. |

## Quick start

```bash
pip install -r requirements.txt

# 1) Verify everything offline (no GPU, no API key):
python test_offline.py

# 2) Serve the models on a GPU (see RUNPOD.md for the cheapest path), then run the safeguards axis:
export OPENAI_BASE_URL=http://localhost:8000/v1
export OPENAI_API_KEY=EMPTY
python run_agents.py \
  --models "safeguarded=unsloth/gpt-oss-20b-BF16,abliterated=huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2" \
  --reasoning-toggle gptoss_effort --framing all --repeats 4 --include-clean

# 3) Statistics with bootstrap confidence intervals:
python stats_exec.py --glob "results/agent_*.json" --metric executed_exfil
```

> The safeguarded and abliterated models have different weights, so **serve them one at a time**
> on the same endpoint and run `run_agents.py` once per model (or point `--base-url` at each).

## Reasoning toggle caveat (report this)

`gpt-oss` is reasoning-native (harmony format) and has **no true "off."** The `gptoss_effort`
toggle maps reasoning **OFF → low effort, ON → high effort**. So the gpt-oss reasoning contrast is
*low vs. high effort*, not *CoT present vs. absent*. Qwen3-style models still get a clean on/off
switch via `--reasoning-toggle qwen_softswitch` / `native`.

## Reproducibility

Every result file records the model id **and** the HF `revision`. Pin the exact checkpoint at
serve time with vLLM's `--revision` and pass the same hash via `label=model@revision` so runs are
reproducible (abliterated community checkpoints get re-uploaded).

## Ethics / scope

This is defensive measurement in a **controlled sandbox**: synthetic canary secrets, simulated
tools, no real credentials or network egress, no real targets. The "no safeguards" (abliterated)
model is used as a **scientific control** to quantify what safety alignment prevents once an agent
can act — not to produce harmful capability.

## Prior work

MCPTox and Invariant Labs (tool-poisoning structure); Arditi et al., NeurIPS 2024 (abliteration /
refusal direction). This framework reuses a benchmark/scoring/sandbox harness from an earlier
single-decision study and reorients it to **modern agent-capable models and real execution**.

License: MIT.
