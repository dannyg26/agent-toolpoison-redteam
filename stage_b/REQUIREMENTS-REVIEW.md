# Requirements review request: does the completed agent study follow the professor's instructions?

Prepared 2026-11-18 for an independent reviewer such as ChatGPT. It is self-contained: no access to the
repository or to earlier conversations is needed. The question is narrow: **does the completed study meet
the professor's three requirements, and where is it weakest?** Do not re-review the statistics or the
runtime code; those were accepted in four earlier review rounds.

## 1. The professor's instructions (verbatim)

> Your plan looks good over all. But the picked model is not fitting what we need. 1. pick more recent
> model, 2. the model should have general agent capability, 3. You are doing the red team, so pick the
> uncersored model.

**Context: what "the picked model" was.** The earlier study in this repository used the following, and the
professor's message responded to that plan:

| Role | Model | Repository created |
|---|---|---|
| Attacker (abliterated) | `huihui-ai/Huihui-Qwen3-8B-abliterated-v2` | 2025-06-18 |
| Attacker (aligned) | `Qwen/Qwen3-8B` | 2025-04-27 |
| Targets | `Qwen/Qwen2.5-7B-Instruct`, `Meta-Llama-3.1-8B-Instruct` | |

That study used StrongREJECT harmful-request prompts, not agent tasks.

## 2. What was done in response (summary)

**Models:**
- **Main red-team attacker:** `huihui-ai/Huihui-Qwen3.8-27B-abliterated`, revision `739e3c5`, an
  "uncensored" abliterated derivative of `Qwen/Qwen3.8-27B`.
- **Matched control:** the aligned original, `Qwen/Qwen3.8-27B` @ `37561816`.
- **Target, the agent being attacked:** `google/gemma-4-26B-A4B-it` @ `4d7ae49`.

**Task:**
- **Benchmark:** AgentDojo v1.2.2, a tool-using agent environment with executable checks, covering
  banking, Slack, travel and workspace.
- **What the attacker does:** writes injection text that is placed into data the target agent reads
  through its tools.
- **Attempts:** up to 3 per case. After each failure the attacker is told whether its text was seen, which
  tools the target called, and the target's reply. It then revises.
- **Success** is AgentDojo's programmatic security check.

**Procedure:**
- 32 held-out cases on 32 distinct user tasks.
- The procedure was frozen and publicly timestamped (git push) before collection, then collected once with
  no deviations.

**Capability check:** both attacker checkpoints acted as the **tool-using agent themselves** on 12 benign
AgentDojo tasks.

**Results:**

| Measure | Uncensored | Aligned |
|---|---:|---:|
| Attack success, 32 paired cases | **17/32** | **16/32** |
| Benign agent tasks completed | **11/12** | **11/12** |
| Attacker outputs with an extractable injection | 69/70 | 68/73 |

- **Paired difference:** +3.1 points (Tango 95% CI −16.5 to +22.7); exact McNemar p = 1.00. No difference was
  detected, which is inconclusive and not equivalence.
- **Same benign failure:** both checkpoints completed the same 11 of 12 tasks. Each executed 59 tool calls
  across the 12-task assessment, and both failed the same task.
- **Baselines:** AgentDojo's fixed template attack scored 10/32; Gemma's clean utility was 27/32.
- **Cost:** $1.94 of GPU time.

## 3. Requirement-by-requirement evidence

### Requirement 1: "pick more recent model"

**Implemented:**
- The attacker generation moved from Qwen3-8B (base April 2025; abliterated June 2025) to Qwen3.8-27B (base
  2026-08-05; abliterated 2026-08-16; pinned weights uploaded 2026-08-24).
- The target moved from 2024-era 7–8B models to Gemma 4 (2026-03-11).

**Evidence (Hugging Face API, checked 2026-11-18):**
- Repository creation dates as above.
- `Qwen/Qwen3.8-27B` belongs to the newest official Qwen LLM generation. The official Qwen releases after
  it are a larger mixture-of-experts sibling, `Qwen3.8-Flash-Next` (2026-08-24, about 180B parameters), and
  image or driving models.

**Newer uncensored checkpoints do exist.** This landscape check was done **after** collection, on
2026-11-18. The original selection rationale recorded in the plan was recency relative to Qwen3-8B, plus
the needs listed in the table's last column.

| Candidate (newer than ours) | Created | Size | Why it was not the pick |
|---|---|---|---|
| `huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated` | 2026-09-29 | ~180B MoE | far too large to serve next to a target on one 80 GB GPU within a $10 budget |
| `huihui-ai/Huihui-Qwen3.8-27B-Coder390-EfficientThink-abliterated` | 2026-10-11 | 27.8B | abliterated from a third-party coding/distillation merge, not the official model, so there is no official aligned counterpart for a matched control |
| `huihui-ai/Huihui-Xing4.0-29B-A4B-abliterated` | 2026-09-29 | 31.2B | smaller-lab base; agent capability less documented; no matched official aligned checkpoint in the plan |
| `huihui-ai/Huihui-Ornith-1.5-35B-A3B-abliterated` | 2026-08-24 | 36.0B | as above |
| Various community "uncensored" fine-tunes, many GGUF-only | Oct–Nov 2026 | various | not servable in the vLLM harness as-is, or no clean aligned counterpart |

The chosen checkpoint is the most-downloaded abliterated build of the newest official dense Qwen model:
about 131k downloads, plus 4.3M for its GGUF version.

**Weak points:**
- "Recent" is relative. The pick was about 3 months old at collection, and newer uncensored checkpoints
  existed.
- A repository date is not a training cutoff.

### Requirement 2: "the model should have general agent capability"

**Implemented:**
- A general-purpose instruction and reasoning model, not a narrow or coding-only one.
- It was checked directly as a **tool-using agent**: each attacker checkpoint did 12 benign AgentDojo user
  tasks with real tool calls, scored by the benchmark's utility check under matched serving and limits.

**Evidence:**
- **Measured, this study:** both checkpoints completed the same 11 of 12 tasks (Wilson 95% interval 65–99%
  each). Each executed 59 tool calls across the 12-task assessment, with no truncation or parse failures.
  Broader preservation of agent capability was not established.
- **Measured, earlier, partial and unmatched:** on BFCL V4, a function-calling benchmark, the uncensored
  checkpoint scored 174/221 official accuracy across 12 categories. Its weakest category was irrelevance
  detection, at 8/20.
- **Measured, pilot:** both checkpoints completed 2/2 benign agent tasks.
- **Publisher-reported, not verified by us:** the Qwen3.8 model card claims improved agentic and
  long-horizon tool use.

**Weak points:**
- **The main open question:** in the attack itself, the uncensored model is an *adaptive attacker that
  writes text using feedback*. It does **not** call tools or act as an autonomous agent during the attack.
  Its agent capability is shown in a separate benign check. If the professor meant that the red-teamer
  itself should operate as a tool-using agent while attacking, the design does not do that.
- 12 tasks is a small check, not comprehensive validation.
- The broader planned capability gate (BFCL plus τ-bench) was never completed. The τ-bench runs were invalid
  because of integration faults, and the aligned checkpoint never ran BFCL.

### Requirement 3: "You are doing the red team, so pick the uncensored model"

**Implemented:**
- The uncensored, abliterated checkpoint is the **main attacker**: the model doing the red-teaming, not the
  model being attacked.
- The aligned original is included only as a **control**, so the study can measure whether choosing the
  uncensored model actually helps. The target is a different model family.

**Evidence:**
- **Publisher-reported:** the model card describes it as "an uncensored version of Qwen/Qwen3.8-27B created
  with abliteration", calls the method "a crude, proof-of-concept implementation", and tags it
  `abliterated` and `uncensored`.
- **Measured, mechanical only:** 69 of 70 uncensored attacker outputs contained an extractable injection,
  against 68 of 73 for the aligned control.

**Weak points:**
- No standard refusal benchmark was run on the checkpoint. "Uncensored" is the publisher's designation and
  does not guarantee zero refusals.
- **The result itself:**
  - The aligned model produced extractable insertion text in 68 of 73 generations. This mechanical count
    does not measure refusal or willingness.
  - No difference in attack success was detected; the comparison remains inconclusive.
  - The study satisfies "pick the uncensored model" without the uncensored model needing to outperform
    the control.
  - Reviewers should judge whether this finding is presented fairly, and whether adding an aligned control
    is consistent with the professor's instruction.

## 4. Questions for the reviewer

1. Does the design satisfy each of the three requirements as worded? Answer **met**, **partly met** or
   **not met** for each, with a reason.
2. **Requirement 1:** is a 2026-08 Qwen3.8-27B abliterated attacker "more recent" enough, given the
   newer-candidate table and the one-GPU, $10 budget? Would you advise switching to one of the newer
   candidates, and if so which one and why?
3. **Requirement 2:** is a separate benign tool-use check adequate evidence of "general agent capability"?
   Or does the requirement more plausibly mean the attacker should itself act as a tool-using agent during
   the red-team? If the latter, what is the smallest design change that would satisfy it?
4. **Requirement 3:** is the uncensored model correctly positioned as the red-teamer? Is including an
   aligned control consistent with the instruction, or does it distract from it?
5. Is anything in §2–§3 overstated: capability claims, the meaning of "uncensored", recency, or the null
   result?
6. What, if anything, should be changed or added before this is sent to the professor? Keep in mind:
   - the $10 ceiling, of which $1.94 has been spent on this run;
   - no human validation;
   - no paid external judges.

**Please answer** with:
- a one-line verdict per requirement;
- the most important weakness;
- concrete, budget-aware recommendations;
- any wording that should change.

## 5. Facts a reviewer may want to verify

| Item | Value |
|---|---|
| Main attacker | `huihui-ai/Huihui-Qwen3.8-27B-abliterated` @ `739e3c5b89849f6c238ce1e5b70008612ae42cdd` |
| Control | `Qwen/Qwen3.8-27B` @ `37561816e66b5b9153b1b64c10968c18c1e6f4a0` |
| Target | `google/gemma-4-26B-A4B-it` @ `4d7ae4984b7db7de8f8457170b3f1a419ee76d52` |
| Benchmark | AgentDojo v1.2.2 (`agentdojo==0.1.35`), no-defence pipeline |
| Serving | vLLM 0.33.0, FP8, one A100-SXM4-80GB |
| Attacker limits | 4,096 tokens, 1,024 thinking budget, temperature 0.6 |
| Target limits | 4,096 tokens, 512 thinking budget, temperature 0 |
| Frozen procedure | public commit `6130230`, pushed before collection |
| Results | commit `506184f` |
| Run | 55.95 min, $1.94; pod terminated; 0 deviations; 0 incomplete pairs |
| Development history, reported separately and not pooled | a Qwen-target smoke run, 0 successes in 44 campaigns, which led to the Gemma target; a 10-case pilot, 6/10 each, with 2 incomplete |
| Repository | `github.com/dannyg26/agent-toolpoison-redteam`, branch `reasoning-safety-removal`, files `stage_b/HELDOUT-RESULTS.md`, `stage_b/AGENT-PAPER-DRAFT.md`, `stage_b/HELDOUT-PROTOCOL.md` |

## 6. Review outcome (2026-11-18)

The reviewer's full response is in [REQUIREMENTS-REVIEW-FEEDBACK.md](REQUIREMENTS-REVIEW-FEEDBACK.md).

**Verdicts:**
1. Recent model: **met**.
2. General agent capability: **met**, with limited empirical scope.
3. Uncensored red-team model: **met**.

**Advice:**
- Keep the pinned model pair; do not switch.
- Make explicit that capability was assessed separately from the attack, during which the attacker does not
  call tools.
- A tool-using attacker would be a separate, frozen follow-up, undertaken only if the professor requires
  that architecture.

**Applied:**
- the five requested wording changes;
- a workflow diagram separating the attack from the capability assessment;
- one benign tool-use example taken from existing capability data.

No data, analysis or classification changed, and no money was spent.
