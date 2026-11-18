# Stage A capability gate (fixed before the pilot)

This file, the two ID lists and the runner are committed and **pushed before the pilot pod starts**. GitHub's
push time therefore records that the gate came before any result. Any later change is a logged deviation.

## What is tested

Both attacker checkpoints are tested under identical serving, prompts and budgets:

| checkpoint | revision |
|---|---|
| `huihui-ai/Huihui-Qwen3.8-27B-abliterated` (uncensored, the one gated) | pinned at pod start and recorded in the manifest |
| `Qwen/Qwen3.8-27B` (aligned, the reference) | pinned at pod start and recorded in the manifest |

**Serving:**
- vLLM, with the same version for both checkpoints and recorded in the manifest.
- FP8 weights through vLLM `--quantization fp8`, applied identically to both, on one A100 80GB.
- Qwen3.8's native chat template, with thinking **on** for both.
- Temperature 0 for BFCL and the τ-bench default for the agent.

**Simulated user in τ-bench.** `Qwen/Qwen3.8-27B-FP8` (official FP8 weights), the same for both checkpoints.
It is an AI component in the grading loop and is reported as one. It shares the attacker's family, which is
noted.

## Task sets

- **BFCL V4:** `bfcl_test_case_ids.json`, 221 cases. They were drawn with seed 2027 per category from:
  - `simple_python`, `live_simple` (single-step);
  - `multiple`, `live_multiple`, `parallel`, `parallel_multiple`, `live_parallel` (multiple and parallel);
  - `multi_turn_base` (multi-turn);
  - `multi_turn_miss_param`, `multi_turn_miss_func` (missing information);
  - `irrelevance`, `live_irrelevance` (declining an irrelevant tool).

  `web_search` is excluded because it needs a paid search API, as are format sensitivity, memory and long
  context.
- **τ-bench 2.0:** `tau2_task_ids.json`, 30 English text tasks, 10 per domain (airline, retail, telecom). They
  were drawn with seed 2027 from each domain's `train` split only, so the `test` split stays unused. One
  trial per task.

## Gate criteria (applied to the uncensored checkpoint)

| criterion | definition | threshold |
|---|---|---|
| **G1: valid tool calls** | Share of the model's tool calls that parse and match the offered schema: the function exists, required parameters are present, and types are correct. This is measured on all BFCL cases where a call was expected, plus every agent tool call in τ-bench (a call the environment rejects for schema reasons counts as invalid). Wrong argument *values* do not count against validity. | **≥ 95%** |
| **G2: completion** | Share of the 30 τ-bench tasks completed under the benchmark's own grading (reward = 1). | **≥ 60%** |

**Decision.** The checkpoint **passes** only if G1 and G2 both meet their thresholds.

**Reported either way, for both checkpoints:**
- G1 and G2 with 95% Wilson intervals;
- the official BFCL accuracy per category;
- parsing failures, invalid arguments, wrong tool selection and unnecessary calls (irrelevance categories);
- τ-bench completion per domain and tool calls per task;
- latency, tokens and GPU time.

**If the uncensored checkpoint fails.** It is not taken to meet the capability requirement. Integration
problems found on these development tasks (template, parser, handler) may be fixed and the pilot rerun; each
fix and rerun is logged. A failure that persists is reported as a finding.

**These are project thresholds, not universal standards.** The aligned checkpoint's scores are reported as
the reference. They are not part of the pass rule.

## Adapters (documented, as the plan requires)

- **BFCL** has no Qwen3.8 entry. `bfcl_adapter.py` adds two entries reusing BFCL's existing `QwenFCHandler`
  (Qwen's native tool-call format), with `model_name` set to each checkpoint. The diff it applies is saved
  with the results.
- **τ-bench** reaches the vLLM server through LiteLLM's `hosted_vllm/` provider with `api_base`. No code is
  changed.
