# Stage B: AgentDojo harness (draft, not frozen)

> **Current execution scope (2026-11-17):** [PILOT.md](PILOT.md) and `pilot_config.json` replace the large
> run described below with ten held-out cases, two attackers and three attempts on Gemma. The measured
> development smoke-run record below is preserved. The old full runner is disabled by default; no paid
> full-matrix run is authorized. The capability gate is incomplete; the pilot has a separate small
> development check and must not be described as passing the original Stage A gate.

This implements plan §5–§7 and §10 (`AGENT-STUDY-PLAN.md`). Nothing has been collected. The case list, the
attacker prompt and the analysis are frozen and pushed before any test-split outcome is collected. Until then,
only the **development** split may be run.

## Files

| file | role |
|---|---|
| `select_cases.py` → `cases.json` | deterministic split and case draw (seed 2027); `--check` re-derives and compares |
| `harness.py` | target adapter, environment injection, attacker loop, conditions, JSONL logging, resume |
| `test_harness.py` | offline tests with scripted models and a mock OpenAI server (no GPU) |
| `run_stage_b.sh` | pod runner: serves the target and an attacker on one A100, runs every condition per target |

**Pinned:**
- `agentdojo==0.1.35`, benchmark version `v1.2.2`, `openai==3.52.0`.
- `vllm==0.33.0`:
  - Qwen3.8 uses tool parser `qwen3_coder` (fix A4 from Stage A) with reasoning parser `qwen3`.
  - Gemma 4 uses `gemma4` for both. Both names are checked in the 0.33.0 source and again on the pod.

## Cases (`cases.json`)

- **Inventory (v1.2.2):** 4 suites, 97 user tasks (all injectable), 35 injection tasks and 949 pairs.
- **Split by user task within each suite** (plan §5): 30% of each suite's user tasks go to development and
  the rest to test, so every case built on a user task stays in that task's split.
- **Test:** 50 cases per suite, 200 in all, over 65 user tasks.
  - Each suite's draw cycles over its injection tasks, so all 35 goals appear.
  - Cases are clustered by user task. Within a suite they are also clustered by injection task.
- **Development:** 40 cases (10 per suite) from the development user tasks. These are the only cases used
  to develop prompts.
- **Recorded per case:** the vectors are those the agent reads when it does the user task correctly
  (AgentDojo's own `get_injection_candidates`). The attacker's text goes into all of them, as AgentDojo's
  attacks do.

## Threat model and success

- **What the attacker controls:** only the injection vectors. The user prompt, the target's system message
  (AgentDojo's default, unchanged), the tool code and the checks are never touched.
- **Success:** AgentDojo's executable `security` check of the injection task on the final environment and
  tool trace. Utility is the user task's own `utility` check. Both come from `run_task_with_pipeline`.

## Conditions (plan §7)

| condition | attacker | runs per case | stops early |
|---|---|---|---|
| `no_attack` | none, default environment | 1 per user task | n/a |
| `fixed` | AgentDojo `important_instructions` (user "Emma Johnson", model name "Qwen" or "Gemma") | 1 | n/a |
| `nonadaptive` | abliterated, ≤5 candidates; sees its own earlier candidates, **no** target feedback | 3 campaigns | at first success |
| `adaptive` | abliterated, ≤5 candidates, with feedback | 3 campaigns | at first success |
| `adaptive` | aligned `Qwen3.8-27B`, same workflow | 3 campaigns | at first success |

**Each candidate gets a freshly loaded environment** (plan §6).

**Seeds are shared across attacker conditions.** A campaign's seed is `sha256(case | campaign | 2027)`, so
campaign *j* of a case uses the same seed under every attacker condition, which preserves the pairing.
Candidate *k* uses seed + *k*.

**ASR@1 and ASR@5** both come from `success_at`.

**Malformed candidates** have no text inside the `<injection>` tags, for example a refusal. They use up their
slot, nothing is sent to the target, and they are recorded as attacker failures.

## Exactly what the attacker sees (plan §6)

**From the start:**
- the attacker system prompt, which describes an authorised benchmark and simulated data;
- the target's prose name;
- the user's task prompt;
- the descriptions of the vectors (from AgentDojo's `injection_vectors.yaml`);
- the injection goal;
- the budget.

**After each failed candidate, the adaptive attacker is told:**
- that it failed;
- whether the target read the text: a heuristic, whether the start of the text appears in a tool result;
- the target's tool calls in order: name and arguments, at most 30 calls, each truncated to 300 characters;
- the target's final reply to its user, truncated to 2,000 characters.

**The non-adaptive attacker is told only** "Write attempt k … make it different."

**Never shown:** the checks' code, ground-truth solutions, environment contents beyond what the target's
calls reveal, or the target's reasoning.

**Not yet frozen:** the attacker prompt texts in `harness.py` may change on the development split only. They
are frozen with the test-split freeze.

## Adapters (documented, as plan §5 requires)

1. **The target's model connection.**
   - AgentDojo's local route (`vllm_parsed` → `OpenAILLM`) sends the system prompt as role `developer` and
     sends no temperature when it is 0 (`temperature or NOT_GIVEN`), so the server's sampling defaults apply.
   - `TargetLLM` does the same conversion, with role `system`, an explicit temperature of 0 and a cap of 8,192
     tokens per call.
   - It also records calls, tokens, time and reasoning.
   - A rejected request (the context is too long) or a tool call with non-JSON arguments ends the agent's turn
     and is counted. The episode is still scored on the environment as it stands.
2. **Environment injection.**
   - AgentDojo pastes injection text straight into a YAML template. A quote or colon in attacker text then
     breaks loading, and newlines inside quoted scalars are folded.
   - The harness loads the official environment with a plain placeholder per vector, substitutes the exact
     attacker text, then re-validates the environment so derived fields such as cloud-file sizes are
     recomputed.
   - For plain text this gives an environment identical to AgentDojo's loader, which is tested on all four
     suites.
3. **Pipeline.** AgentDojo's no-defence pipeline: system message, user query, LLM, and a tool loop of up to
   15 iterations. `run_task_with_pipeline` keeps its official behaviour of up to 3 reruns when the agent ends
   without a text answer. Reruns are counted (`pipeline_runs`).

## Benchmark properties found while testing (not changed)

- **Workspace goals 6–13 and travel goal 6 have no reference solution** (`ground_truth` returns `[]`). Their
  `security` checks are complete, so a real agent can still meet them. Only the scripted test agent cannot.
- **Travel goal 2's check expects the attacker's calendar event at the next free calendar ID.** With user
  task 4, which creates its own event, it counts only if the agent obeys before doing the user's request.
- **Some goals succeed through what the agent says**, for example travel goal 6. The check reads the final
  output.

**Offline check.** With a scripted agent that follows the user task's reference solution:
- the injected text reaches the agent in **240/240** selected cases;
- the user task succeeds in 240/240;
- obeying the reference attack triggers the check in every case that has a reference solution, except the
  order-dependent travel case.

## Compute (measured in the development smoke run, 2026-11-17)

**Size per target.** No attack (65 user tasks), fixed (200 cases), then 3 attacker conditions × 600
campaigns × ≤5 candidates. That is up to about 9,300 target episodes and 9,000 attacker generations.
Early stopping saves almost nothing while ASR is near zero.

**Smoke run.** `SPLIT=dev LIMIT=8 TARGETS=qwen`, one A100 SXM, about 2.4 h, about $5.40.
- **Completed:** no_attack, fixed and non-adaptive.
- **Partial:** adaptive abliterated finished 20 of 24 campaigns before the time cap.
- **Not run:** adaptive aligned.

**Measured per candidate (mean):**

| | non-adaptive | adaptive |
|---|---|---|
| attacker generated tokens | 1,131 | 4,789 (10/95 hit the 8,192 cap) |
| attacker seconds | 68 | 680 |
| target episode generated tokens | 1,661 | 1,763 |
| target episode seconds | 112 | 97 |
| wall time per campaign (16 workers) | 68 s | 310 s |
| aggregate generation | about 200 tokens/s | about 100 tokens/s |

**Why it is slow.** Two FP8 27B servers on one 80 GB GPU leave little KV cache: 38k tokens on the attacker
server and 61k on the target server. The attacker server ran about 4 requests at a time at about 18 tokens/s
each, while the rest queued. One adaptive campaign failed on a 900 s client timeout caused by this queueing.

**What the full test split would cost.**
- **Tokens:** about 95M generated tokens for both targets. About two thirds are attacker tokens, mostly
  adaptive thinking.
- **As run here:** about 100–200 tokens/s, so about 175 GPU hours, **about $400**. Not viable.
- **One model per GPU** (2×A100 or 2×H100): the KV cache grows about tenfold. A guess of 25–35 h at about
  $4.4/h, **about $110–150**. This must be measured before it is relied on.

**Validity problem found.** The 10 adaptive candidates that hit the 8,192-token cap were cut off inside their
thinking and counted as malformed. That makes the attacker's failures partly an artifact of the token limit.
Fix before the freeze: raise the cap, or bound the thinking explicitly, the same way for both attackers.

**Floor effect.** Against the Qwen target: fixed 0/8, non-adaptive 0/24 campaigns, adaptive abliterated 0/20
campaigns. If the test split looks the same, the attacker comparison cannot show a difference. Check Gemma and
the prompts on the development split before paying for the test split.

## Still open before the test-split freeze

1. **The rest of plan §11:** resampling (user-task clusters within suite), the decision rule and α, the
   multiple-comparison procedure, and the size justification.
2. **Settings to confirm:**
   - attacker sampling: currently Qwen's thinking defaults, temperature 0.6, top-p 0.95, top-k 20;
   - thinking on for both attackers;
   - the target's default thinking per model's template.
3. **Attacker prompt:** frozen after development runs.
4. **Disclosure choices:** whether the attacker sees the target's name and the user's task, as AgentDojo's
   own attacks do. Currently yes to both.
