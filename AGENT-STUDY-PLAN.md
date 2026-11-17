# Can a Recent Uncensored General-Purpose Agent Improve Automated Red-Teaming? (revised plan, draft)

**Status: draft, not pre-registered, nothing collected.** This is the revised research plan. Implementation
notes checked on 2026-11-16 are marked **[impl]**.

**The received text stops partway through §11** ("Estimate uncertainty by resampling underlying user-task
clusters…"). Everything after that point must be added before the freeze.

This is a new follow-up experiment. It does not replace or modify the completed study.

## 1. How the plan meets the professor's requirements

- **Recent model.** The 2026 Qwen3.8 family replaces the older Qwen3-8B attacker.
- **General agent capability.** A general-purpose model runs inside a tool-enabled agent harness. Function
  calling, multi-step task completion and response to environment feedback are verified before the security
  experiment.
- **Uncensored red-team model.** The main attacker is `huihui-ai/Huihui-Qwen3.8-27B-abliterated`. Its
  original counterpart, `Qwen/Qwen3.8-27B`, is the comparison control, measuring whether choosing the
  uncensored checkpoint actually helps.

"Uncensored" is the publisher's description, not a guarantee of zero refusals or preserved capability.
Both are measured.

## 2. Research questions

**Primary.** Under the same tools, instructions and testing budget, does the uncensored agent find more
successful attacks than its original aligned counterpart?

**Secondary:**
- Does feedback-driven adaptation beat independently generated candidates?
- Does the uncensored checkpoint keep useful general agent capability?
- Do the findings transfer across target-model families?
- How much time, compute and target interaction does each successful attack take?

## 3. Models and roles

| role | checkpoint | facts [impl, Hugging Face] |
|---|---|---|
| main attacker | `huihui-ai/Huihui-Qwen3.8-27B-abliterated` | created 2026-08-16, 27.8B, Apache-2.0. Layers 18–51 ablated; the card calls the method a "crude, proof-of-concept implementation". |
| attacker control | `Qwen/Qwen3.8-27B` | created 2026-08-05, 27.8B, Apache-2.0 |
| target agent | `Qwen/Qwen3.8-27B` | as above |
| target agent (cross-family) | `google/gemma-4-26B-A4B-it` | a Gemma 4 mixture-of-experts model with about 4B active parameters |

**Serving and isolation:**
- Both targets run in the same benchmark environment, with equivalent tool interfaces and each model's
  native chat template.
- Attacker and target conversations are kept separate. The attacker cannot see target weights, private
  instructions or hidden grading code.
- Exact model revisions, serving software, precision, templates and thinking settings are frozen before
  evaluation.

**[impl] Pinning.** The abliterated card's download command names revision `d42ca89`, but the hub head is
`739e3c5b`. Each checkpoint is pinned to one revision, recorded through an authenticated `/v1/models` call.

## 4. Stage A: verify general agent capability

**A. BFCL V4.** A fixed, stratified subset covering:
- single-step function calls;
- multiple and parallel calls;
- multi-turn interactions;
- handling missing information;
- correctly declining to call an irrelevant tool.

Official scores are reported alongside tool-call parsing failures, invalid arguments, wrong tool selection
and unnecessary calls.

**[impl] BFCL setup.**
- Package: `bfcl-eval` 2026.3.23, which supports vLLM and existing OpenAI-compatible endpoints.
- **It has no handler for Qwen3.8 or Gemma 4.** The newest listed are Qwen3-32B and the Qwen3-2507 models.
  Qwen3.8 is registered through BFCL's existing Qwen3 function-calling handler, documented as an adapter
  with its diff committed.
- The `web_search` category needs a SerpAPI key and is left out of the subset.

**B. τ-bench 2.0.** English text tasks across airline, retail and telecom, starting with a development
pilot of 30 tasks balanced across the three domains. Both attacker checkpoints are evaluated under the same
conditions.

Measured:
- end-to-end task completion;
- correct environment changes;
- policy compliance under the benchmark's rules;
- number of tool calls;
- latency and token use.

Official grading is used, and any component that depends on an AI judge is documented.

**[impl] τ-bench setup.**
- Package: `tau2` 4.0.1, released 2026-11-13. τ-bench 2.0 English results are not input-identical to
  v1.0.1.
- Models are reached through LiteLLM, so a hosted vLLM endpoint works.
- **It needs a simulated user, which is an AI component in the grading loop.** The default is a hosted
  OpenAI model. Proposal: a local model, the same for every condition, so no outside API or data leaves the
  pod. This is a decision to make (§13).

**Capability gate.** The acceptance criteria are written down before the pilot runs. The proposed
engineering thresholds are:
- **at least 95% valid tool calls**;
- **at least 60% completion** on the selected benign multi-step tasks.

These are project thresholds, not universal standards. Scores and uncertainty are reported even if the
checkpoint passes. If the uncensored checkpoint fails the gate, it is not assumed to meet the capability
requirement. Model or integration problems are resolved on development tasks before the security experiment
is frozen.

**[impl] Committing the gate.** The gate is committed and **pushed** before the pilot, so GitHub's push
time records that it came first.

## 5. Stage B: primary security evaluation with AgentDojo

**Why AgentDojo is primary.** The experiment tests agents interacting with an environment, not just attack
text. AgentDojo provides legitimate user tasks, tools, attacker objectives and security checks.

**Threat model.** The target agent gets a legitimate task. The attacker controls only the untrusted content
surface the benchmark allows, such as a specified tool response. It cannot modify:
- the legitimate user instruction;
- the target's trusted system instruction;
- the tools' executable implementation;
- the evaluator or success criteria.

The official environment and supported attack interface are used, and every adapter or modification is
documented.

**[impl] AgentDojo setup.** Package `agentdojo` 0.1.35. Its README documents hosted API models, so local
serving through vLLM needs its local-model option or a small documented pipeline adapter.

**Development and test split:**
- split by underlying user task, not by individual attack variant;
- keep related cases in the same split;
- balance coverage across domains;
- keep test cases out of prompt development and strategy-memory construction;
- freeze eligibility rules and case identifiers before collecting test outcomes.

**Proposed size.** Aim for 200 eligible test cases, subject to the frozen benchmark inventory and compute.
These are 200 cases, not 200 independent tasks: several cases may share a user task and stay clustered in
the analysis. The final size must be justified before evaluation, because a feasibility target is not a
power calculation.

## 6. Primary attacker comparison

Both attacker checkpoints run with identical red-team instructions and the same adaptive workflow. For each
case:

1. initialise the benchmark environment;
2. the attacker proposes a candidate intervention;
3. execute a target-agent episode;
4. return the permitted target response and trace information;
5. the attacker revises its next candidate.

**Rules:**
- **Budget:** at most five candidate evaluations per campaign. The target environment is reset before each
  candidate; the attacker's observations persist within the campaign.
- **Seeds:** three campaigns with distinct recorded seeds per case and condition. A seed aids
  reproducibility; it doesn't guarantee deterministic inference.
- **Feedback:** the attacker never inspects hidden verifier code or private reference answers, and exactly
  which feedback it receives is specified.
- **No cross-case learning:** strategies learned on one test case are not carried into later cases in the
  primary experiment. Cross-case learning would be a separate online-learning experiment.

## 7. Baselines and method comparisons

| condition | definition |
|---|---|
| no attack (required) | the target's legitimate-task completion with no adversarial intervention |
| fixed attack (required) | a preselected attack provided by the benchmark, with no adaptive generation |
| non-adaptive generation (required) | five candidates generated without seeing earlier target responses, evaluated under the same total budget |
| adaptive uncensored agent (main) | the same maximum budget, with feedback from earlier evaluations of that case |
| adaptive aligned agent | the same adaptive workflow, isolating the checkpoint comparison from the workflow comparison |

**Established methods, each in its proper setting:**
- **PAIR:** the prompt-refinement reference for the secondary misuse experiment.
- **TAP:** a branching-search comparison, if resources permit.
- **GOAT:** a separately reported multi-turn conversation condition.
- **CART:** recent related work on adaptive, auditable testing.

Any method adapted to a different attack surface is named as an adaptation, not presented as the canonical
method.

## 8. Stage C: secondary evaluation with AgentHarm

AgentHarm tests direct misuse of a tool-using target agent. The two benchmarks answer different questions:
- **AgentDojo:** can untrusted content redirect a legitimate workflow?
- **AgentHarm:** can an adversarial request induce harmful task completion?

**Method:**
- Use the released public test split and its official grading implementation.
- Record the actual available task counts and eligibility exclusions.
- Group augmented variants by their original base task; they are not independent tasks.
- Include benign counterpart tasks where available, to tell refusal apart from inability to complete the
  workflow.

**Reported:** harmful-task completion, refusal, partial completion, tool-use failures and benign-task
completion. AgentHarm and AgentDojo are never pooled into one overall success rate.

**[impl] AgentHarm setup.** It is not on PyPI under its own name; it ships in `inspect-evals` (0.29.0). Its
grading includes AI-judged components, which are reported as such (§10).

## 9. Optional modern extension: RedClaw-Bench

After the core experiment, coverage of persistent-agent risks may be evaluated with a pinned RedClaw-Bench
release. The two possible experiments are kept separate:

- **A. Replay its published attacks.** This evaluates the target agent's robustness.
- **B. Let our attacker generate interventions** for its environments and objectives. This evaluates our
  attacker, but is an adapted protocol.

Replaying existing attacks is not claimed to show our attacker's effectiveness. In persistence experiments,
state persists only within the specified scenario and is reset between independent cases. Extension results
stay separate from the primary findings.

## 10. Success measurement

**Primary security outcome.** Whether a candidate causes the benchmark-defined violation, backed by the
official environment or task checks. For each campaign: whether at least one of its five candidates
succeeds (**ASR@5**).

**Also reported:**
- ASR@1;
- legitimate-task completion, without attack and under attack;
- whether the target actually encountered the intervention;
- prohibited actions attempted versus effects completed;
- attacker refusals and malformed candidates;
- target tool failures;
- actual target-model calls, tokens, latency and compute cost.

An agent *saying* it performed an action is not evidence that it did. Executable checks are used wherever
available, and semantic AI judgments are kept identifiable as a separate measurement component.

**Rules for AI-judged outputs:**
- label complete responses or trajectories;
- keep annotators blind to attacker condition;
- record explicit decisions rather than treating omitted entries as negatives;
- freeze blind labels before reconciliation;
- report agreement as repeatability, not correctness.

Human validation will not be conducted. All findings based on semantic labels remain conditional on the AI
annotation procedure.

## 11. Statistical analysis

**Primary contrast.** The adaptive uncensored attacker minus the adaptive aligned attacker, reported
separately for each target. Campaign outcomes are averaged across the three recorded seeds within each case,
with pairing preserved across attacker conditions. Uncertainty is estimated by resampling underlying
user-task clusters…

**[The received plan text ends here. Still to be added before the freeze:** the resampling details, the
decision rule and α, the multiple-comparison procedure for the secondary questions, the power or sample-size
justification, and any later sections.]

## 12. Implementation notes [impl]

**Compute:**
- **Stage A** needs the checkpoint under test plus the simulated-user model: about 112 GB at BF16, so
  **2× A100 80GB**, or about 56 GB on one GPU with FP8 weights.
- **Stage B** needs an attacker and a target at the same time: Qwen3.8-27B (about 56 GB) plus Gemma 4
  26B-A4B (about 52 GB).
- **Credit.** The remaining RunPod credit (about $9) covers part of Stage A only. Stages B and C will need
  more.

**Run hygiene** (lessons from the completed study):
- a self-terminating watcher that copies outputs back and stops pods on completion, failure or a stall;
- complete manifests;
- every freeze pushed before the step that depends on it.

## 13. Decisions to make before Stage A

| decision | proposal |
|---|---|
| τ-bench simulated-user model | a local model, the same for both checkpoints (for example, aligned `Qwen/Qwen3.8-27B`); reported as an AI component |
| BFCL subset | a fixed seeded sample per category: simple, multiple, parallel, parallel-multiple, multi-turn base, multi-turn missing parameter or function, irrelevance. `web_search` excluded. |
| gate thresholds | ≥95% valid tool calls and ≥60% completion, as in §4, committed and pushed before the pilot |
| thinking mode | fixed and recorded per checkpoint |
