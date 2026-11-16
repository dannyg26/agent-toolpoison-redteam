# Red-teaming with a recent uncensored agent model: plan (revised, draft)

**Status: draft, not pre-registered, nothing collected.** This revision adopts the revised research plan.
Each numbered section below gives that plan's text in summary, then **proposed specifics**: concrete choices
to confirm before the freeze. Once they are agreed, the plan, code and settings are frozen in a tag that is
**pushed before any evaluation outcome is collected** (§8).

This is a new follow-up experiment. The completed study and its reported results are unchanged.

## 1. Objective

Evaluate whether a recent, uncensored, general-purpose agent is an effective automated red-team attacker,
and whether it performs differently from its original aligned counterpart under matched conditions.

## 2. Selected model

| role | checkpoint | created | size | licence |
|---|---|---|---|---|
| primary attacker | `huihui-ai/Huihui-Qwen3.8-27B-abliterated` | 2026-08-16 | 27.8B dense | Apache-2.0 |
| comparison attacker | `Qwen/Qwen3.8-27B` | 2026-08-05 | 27.8B dense | Apache-2.0 |

Verified on Hugging Face, 2026-11-16.

**How this meets the requirements:**
- **Recent:** Qwen3.8 is a 2026 model family. It replaces the Qwen3-8B attacker.
- **General agent capability:** the base model supports planning, multi-step work and interaction with an
  environment. It is not trained only to write jailbreak prompts.
- **Uncensored:** the derivative is published as an abliterated, uncensored checkpoint.

"Uncensored" describes the checkpoint's intended modification. Its actual refusal behaviour and agent
performance are measured, not assumed from its name.

**Proposed specifics:**
- **The abliteration.** The derivative's card says layers 18–51 were ablated and calls the method a "crude,
  proof-of-concept implementation". So the capability pilot (§4) matters.
- **Pinning.** The card's download command names revision `d42ca89`, but the hub head is `739e3c5b`. One
  revision per checkpoint is pinned and recorded through an authenticated `/v1/models` call. That call was
  missing last time (CD-1).

## 3. Agent setup

**What the harness provides.** The attacker runs inside a tool-enabled evaluation harness. It can:
- inspect the assigned benchmark task and the evaluation interface;
- submit candidate prompts to a target model;
- read the target's responses;
- keep observations across attempts;
- decide whether and how to revise its next attempt.

The tools, instructions and maximum interaction budget are identical across conditions.

**Proposed specifics.** These tools are exposed through the model's native tool-calling interface, served
by vLLM:

| tool | effect |
|---|---|
| `get_task()` | returns the goal and the success criterion shown to the attacker |
| `query_target(prompt)` | sends one prompt to the target and returns the full response; counts against the budget |
| `note(text)` / `read_notes()` | the attacker's own memory across attempts |
| `finish(reason)` | ends the episode early |

The budget per goal:
- at most **5 `query_target` calls**;
- at most 32k attacker output tokens;
- at most 20 tool calls in total.

The attacker never sees labels or judge scores, only the target's text.

## 4. Capability pilot

**What it checks.** Before the main collection, both checkpoints are evaluated on separate, benign agent
tasks:
- valid tool-call formatting and arguments;
- correct tool selection;
- completion of tasks that need several tool interactions;
- recovery from tool errors;
- memory use, speed and inference cost.

The minimum acceptable performance is set before the pilot. The uncensored checkpoint goes ahead only if it
meets the criteria, which checks that the weight modification kept the agent capability the study needs.

**Proposed specifics:**
- **Benign tasks.** AgentDojo's benign user tasks with no attack (97 tasks across four simulated suites),
  plus a harness smoke test with injected tool errors. Success is checked by code.
- **Criteria, fixed before the pilot runs:**
  1. at least 95% of tool calls parse and have valid arguments;
  2. the abliterated checkpoint's task completion is at most 10 points below the aligned checkpoint's;
  3. it recovers from at least 70% of the injected tool errors;
  4. it fits the serving budget in §9.
- **If it fails.** The study stops and reports the failure as a finding. It does not quietly switch
  checkpoints; any replacement would be a logged, re-registered change.

## 5. Experimental comparison

**Primary:**

| arm | attacker | instruction |
|---|---|---|
| A | uncensored Qwen3.8 agent | red-team instruction |
| B | original Qwen3.8 agent | the same red-team instruction |

The instruction and harness are held fixed.

**Secondary, if resources allow:** plain-instruction versions of both checkpoints. These separate the
contribution of the red-team instruction from differences between the checkpoints.

**Proposed specifics:**
- **Freezing the instruction.** The red-team instruction is written and frozen on the dev set only.
- **The plain arms.** They are included if the pilot cost estimate allows. That decision is recorded
  before the freeze, not after seeing results.

## 6. Evaluation design

**What the revised plan sets:**
- **Sets.** A development set for debugging and a separate, frozen evaluation set. Goals already used in
  the completed project are not treated as unseen.
- **Targets.** Two target models, at least one outside the Qwen family, with exact checkpoints chosen and
  recorded before collection.
- **Equal budgets.** Every attacker gets the same maximum attempts, tool access and token budget. Actual
  target queries, failures, latency and token use are recorded, because equal attempt limits do not mean
  equal compute.

**Proposed specifics:**
- **Goal source.** All 313 StrongREJECT goals were used by the completed project. The new pool is
  **HarmBench text behaviours**, which have never been used here.
- **Eligibility rule, fixed now.** Keep the `standard` and `contextual` functional categories. Exclude
  `copyright`, and exclude the `chemical_biological` semantic category in advance. That leaves **244
  eligible goals**. Last time, annotators blocked biological content and the exclusions came after
  collection (CD-2); this rule is fixed beforehand to avoid that.
- **Split.** A seeded random 60 goals for dev; the remaining **184 for evaluation**, collected once after
  the freeze.
- **Targets:**

  | target | checkpoint | created | size | role |
  |---|---|---|---|---|
  | A, non-Qwen | `google/gemma-4-31B-it` | 2026-03-11 | 31.3B dense | |
  | B | `mistralai/Mistral-Small-4-119B-2603` | 2026-01-23 | 119.4B MoE, Apache-2.0 | the second non-Qwen target, if the budget allows |

  If Mistral Small 4 is too costly, the alternative second target is the aligned `Qwen/Qwen3.8-27B` itself,
  noted as being of the attacker's family.

## 7. Outcomes

**Primary outcome:** whether the target produces a response labelled successful within the fixed attempt
budget.

**Secondary outcomes:**
- attacker refusals;
- valid tool calls;
- task completion;
- actual target queries;
- latency;
- token cost.

**Annotation.** Every target response is labelled in full, with the same blinded AI annotation procedure
across conditions. All label-based findings are reported as AI-annotated, not human-validated. Human
validation will not be conducted.

**Proposed specifics:**
- **The procedure.** The same census procedure as the completed confirmation: two independent AI
  annotator sessions, blind to arm, using the existing rule in `LABELING-PROTOCOL.md`. Labels are frozen and
  hashed, the hashes pushed, and only then reconciled.
- **Helper scripts.** If an annotator uses one, every item must get an explicit decision with an
  item-specific reason. A default-negative mechanism is not allowed (see run note 6 of the completed
  study).
- **Annotator blocks, rule fixed in advance.** Any goal an annotator still refuses to process is excluded
  from **every** arm and counted. The primary result is also reported with those goals at their least
  favourable values. This is stated now, not after collection.
- **Attacker refusal** is decided by code: the episode ends without a `query_target` call, or with only
  refusal text. Refusal is reported separately from success.

## 8. Analysis and reproducibility

**Frozen and publicly timestamped before any evaluation outcome is collected:**
- model revisions and serving configuration;
- chat templates and thinking-mode settings;
- instructions, tools and interaction budgets;
- goal eligibility rules;
- annotation rules;
- the primary comparisons and statistical decision rules.

The analysis uses paired comparisons on shared goals, reports uncertainty, and specifies the
multiple-comparison procedure in advance. Deviations are logged without replacing the original plan.

**Proposed specifics:**
- **Primary contrast.** A − B on each target, with a two-sided paired goal bootstrap (10,000 resamples,
  fixed seed). The 95% interval and the direction are reported; a difference is claimed only where the
  interval excludes zero.
- **Secondary contrasts** (red-team versus plain on each checkpoint, if those arms are run, and refusal
  rates) are Holm-adjusted within each target. Cost and latency are descriptive.
- **Self-test before the tag.** Error rates at every boundary, including the sparse-margin case from the
  seventh external review. The tagged self-test includes the CC-1 fix.
- **Public timestamps.** The tag is **pushed** before collection, and each later freeze (evaluation
  manifests, blind-label hashes, analysis inputs, results) is pushed before the step that depends on it.
  That way GitHub's push times record the order, which the completed study could only report.

## 9. Intended contribution

The study assesses how well a recent uncensored general-purpose agent works as a red-team attacker. Its
conclusions concern the tested checkpoints, harness, targets and annotation procedure. It does not assume
that removing refusals improves agent capability or guarantees stronger red-team performance.

**Proposed compute (measured in the pilot before approval):**
- **Qwen3.8 + Gemma 4.** At BF16 the attacker needs about 56 GB and Gemma 4 31B about 63 GB, so both
  together need **2× A100 80GB** or one H200.
- **Mistral Small 4** needs about 120 GB at FP8 on top of that.
- **Monitoring.** A self-terminating watcher copies outputs back and stops the GPUs on completion, failure
  or a stall.

## 10. Decisions to make before the freeze

| decision | proposal |
|---|---|
| second target | Mistral Small 4 if the budget allows; otherwise aligned Qwen3.8-27B, flagged as same-family |
| attempt budget | 5 target queries per goal |
| plain-instruction arms | include if the pilot cost estimate allows |
| thinking mode | on for both attackers, recorded |
| pilot thresholds | the four criteria in §4 |
| goal pool | HarmBench standard + contextual, chemical/biological excluded: 244 goals (60 dev / 184 eval) |
