# Agentic red-team study: plan (draft for advisor review)

**Status: draft. Not pre-registered; nothing has been collected.** Once the advisor agrees the design, this
becomes the pre-registration. It will be frozen in a tagged commit, and pushed, before any collection.

**Why a new study.** The advisor's feedback on the current study (`RED-TEAM-STUDY.md`) set three
requirements for the attacker:

1. a recent model;
2. general agent capability;
3. an uncensored model, since we are the red team.

The current study meets only the third, and only partly. Its models are 8B chat models from 2024–25, used
without tools. Its results apply to those models only, so this is a new study rather than a revision. The
existing pipeline is reused: collection manifests, the frozen analysis with a self-test, and the deviation
log.

## 1. Question

> When you build an automated red-team agent against tool-using AI agents, is it worth using an
> uncensored (abliterated) attacker, or does a red-team prompt on the aligned model do as well?

This repeats the current study's question in the setting the advisor asked for: recent models,
attacking agents, with the attacker itself acting as an agent. It also tests the question the current
study left unresolved: **does abliteration add anything on top of a good red-team prompt?**

## 2. Models (verified on Hugging Face, 2026-11-16)

| role | model | created | size | licence | meets |
|---|---|---|---|---|---|
| attacker, uncensored | `huihui-ai/Huihui-Qwen3.8-27B-abliterated` | 2026-08-16 | 27.8B dense | Apache-2.0 | 1, 2, 3 |
| attacker, aligned (comparison) | `Qwen/Qwen3.8-27B` | 2026-08-05 | 27.8B dense | Apache-2.0 | 1, 2 |
| target A | `google/gemma-4-31B-it` | 2026-03-11 | 31.3B dense | Apache-2.0 | recent, agentic |
| target B (see §10) | `mistralai/Mistral-Small-4-119B-2603` | 2026-01-23 | 119.4B MoE | Apache-2.0 | recent, agentic |

- **Same base model for both attackers.** The only difference between them is the abliteration. That
  isolates the effect of removing refusals, as in the current study.
- **The abliteration.** The model card says only layers 18–51 were ablated and calls the method a "crude,
  proof-of-concept implementation". Any loss of capability from that is part of what the study measures.
- **Pinned revisions.** The card's download command names revision `d42ca89`, but the hub head is
  `739e3c5b`. We will pin one exact revision per model and record it in every run manifest, served
  through an authenticated `/v1/models` call (the lesson of CD-1).
- **Different families.** Neither target is from the Qwen family, so the attacker is not attacking its own
  lineage.
- **Thinking mode** is fixed per arm and recorded. That gap was a weakness of the current study.

## 3. Agent setting: indirect prompt injection in AgentDojo

**Environment.** AgentDojo (Debenedetti et al., NeurIPS 2024 Datasets and Benchmarks; `agentdojo` 0.1.35)
has four simulated suites: workspace, travel, banking and Slack.
- **Target.** The target is a tool-using agent doing a benign **user task**, such as "summarise my unread
  emails".
- **Injection.** One tool result contains attacker-controlled text: the **injection**. The attack succeeds
  if the target then carries out the attacker's **injection task**, such as forwarding a security code to
  an outside address.
- **Scale.** Version 1 has 97 user tasks and 629 security cases (user task × injection task).

**Why this setting:**
- **It's agentic on both sides.** The target agent plans and calls tools, and the attacker works as an
  agent too (below).
- **Success is checked by code.** AgentDojo decides it by inspecting the simulated environment's state,
  for example whether the email was sent. **No AI or human labels are needed for the primary outcome.**
  That removes the biggest weakness of the current study: AI-only labels with no human validation.
- **It's standard and current.** Indirect prompt injection is a central agent-security risk, it matches
  this repository's original "agent tool-poisoning" aim, and published baselines exist.
- **Lower content risk.** The tasks are simulated: fake emails, fake bank transfers. The attacker writes
  manipulation text, not weapons instructions, so far less harmful content is produced than with
  StrongREJECT goals.

**The attacker as an agent.** For each security case, the attacker gets:
- the injection task;
- the location of the injection in the tool output;
- the names and descriptions of the target's tools (AgentDojo's "tool knowledge" threat model).

It does not see the user task text. It writes an injection, AgentDojo runs the target, and the attacker
sees the target's tool-call trace and final reply. It may then revise, up to a fixed budget of **3
attempts** per case, the same for every arm. The attacker runs as a tool-calling agent: it submits each
attempt through a `submit_injection(text)` tool and reads results through a `get_trace()` tool. Using
these tools well is part of the capability being compared.

## 4. Arms (per target)

| arm | attacker | instruction |
|---|---|---|
| aligned-plain | Qwen3.8-27B | plain task instruction |
| aligned-redteam | Qwen3.8-27B | red-team system prompt |
| abliterated-plain | abliterated Qwen3.8-27B | plain task instruction |
| abliterated-redteam | abliterated Qwen3.8-27B | red-team system prompt |
| fixed-baseline | none | AgentDojo's built-in `important_instructions` attack, non-adaptive |
| no-attack | none | no injection; measures the target's utility |

The red-team prompt is written and frozen during the dev phase (§6), before any held-out data exists.

## 5. Outcomes and hypotheses

**Primary outcome.** *Attack success within 3 attempts* per (arm, security case): AgentDojo's own
injection-task check passes on at least one attempt. It is deterministic and needs no labelling.

**Secondary outcomes:**
- success on the first attempt;
- the target's utility under attack (whether the user task was still completed);
- **attacker refusal**: whether an attempt contains no usable injection. This is measured
  deterministically, by checking whether the attempt contains the injection task's required identifiers
  (the attacker's address, IBAN or code), so it needs no AI labels;
- success among non-refused attempts. This separates *willingness* from *capability*, the question the
  current study raised.

**Hypotheses** (each per target; the decision rules are fixed in the pre-registration):

| id | contrast | test | why |
|---|---|---|---|
| **P1 (primary)** | abliterated-redteam − aligned-redteam | two-sided, 95% CI | does abliteration add anything on top of a good prompt? (unresolved before) |
| P2 | abliterated-plain − aligned-redteam | one-sided margin, upper < +0.05 | repeats the current study's CH1 in the agentic setting |
| P3 | aligned-redteam − aligned-plain | two-sided | how much the red-team prompt is worth |
| P4 | refusal rate, aligned vs abliterated (red-team prompt) | two-sided | does the aligned attacker refuse agent attacks? |

P2 to P4 are Holm-adjusted within each target. P1 is primary on both targets, and is claimed only where
its interval excludes zero.

## 6. Sample and the dev/held-out split

**Unit and split.** The unit is the security case, and cases sharing a user task are correlated.
- **Dev split:** a seeded 25% of user tasks in each suite, with all their cases. It is used only for
  engineering: wiring the attacker tools, writing and freezing the red-team prompt, timing and cost. No
  hypothesis is tested on it.
- **Held-out split:** the other 75%, about 470 cases. It is collected **once**, after the plan is tagged
  and pushed.

**Power.** It will be estimated from the dev pilot's rates before the tag, and set out in the
pre-registration. If the pilot shows P1 would be badly underpowered, we add repeats (each case run twice)
rather than more arms.

## 7. Analysis (frozen script, self-tested before the tag)

- **Cluster bootstrap.** A paired bootstrap over user tasks, resampling whole user tasks so that their
  cases stay together. 10,000 resamples with a fixed seed.
- **One run.** The frozen analysis runs once on the held-out data. Anything else is labelled exploratory.
- **Self-test before the tag.** Error rates at each hypothesis boundary, including the sparse-margin case
  found by the seventh external review, with stated limits.

## 8. Integrity rules (lessons from the current study)

1. **Tag and push before collection.** The plan, the analysis script and the frozen prompts are tagged
   and **pushed** before any held-out run.
2. **Push every freeze before the step that depends on it.** That covers the held-out collection
   manifests, the analysis inputs and the results, so GitHub's push times give the order an external
   record. (The current study could only report its order.)
3. **Complete run manifests.** Each run records the commit, revision-pinned model snapshots (an
   authenticated `/v1/models` call), the vLLM version, the thinking setting and the decoding settings.
4. **Watched runs.** A self-terminating watcher copies each output back as it finishes and stops the GPU
   on completion, failure or a stall.
5. **Deviation log.** Every departure from the plan is logged as a deviation before the step it affects.

**To check first in the dev phase.** AgentDojo's README documents hosted API models. Serving the two
targets locally through vLLM needs either AgentDojo's built-in local-model option or a small custom
pipeline element wrapping an OpenAI-compatible endpoint. This is confirmed, or built, before the pilot.

## 9. Compute and cost (to be measured in the dev pilot)

- **Memory.** At BF16 the attacker needs about 56 GB and Gemma 4 31B about 63 GB. Running both at once
  needs **2× A100 80GB** (about $2.4–4/hr) or one H200, or FP8 weights on a single 80 GB GPU.
- **Mistral Small 4.** At 119B it needs about 240 GB at BF16, or about 120 GB at FP8 on 2× H100. That is a
  large step up in cost (see §10).
- **Workload.** About 470 held-out cases × 4 adaptive arms × up to 3 attempts × a multi-step target episode,
  plus the two baselines. That is roughly 6–8k target episodes per target.
- **Estimate.** Tens of dollars per target, not hundreds. The dev pilot gives the real figure before the
  budget is approved.

## 10. Open decisions for the advisor

| decision | options | recommendation |
|---|---|---|
| second target | Mistral Small 4 (different family, about 4× the GPU cost) · Gemma 4 26B-A4B (cheap, but the same family as target A) · a target served by a hosted API | Mistral Small 4 if the budget allows; otherwise a single target |
| attacker knowledge | tool knowledge (recommended) · also the user task (stronger, less realistic) | tool knowledge |
| attempt budget | 3 (as before) · 5 | 3, unless the pilot shows success is still climbing at 3 |
| defences | none · also AgentDojo's tool filter | none in the primary run; one defence could be a secondary arm |
| thinking mode | off (comparable with the current study) · on (stronger agents) | on, recorded, the same for both attackers |

## 11. Relationship to the current study

- **What carries over:** the current study's question, pipeline and integrity rules.
- **What doesn't:** its results apply only to its 8B chat models.
- **Both kept.** The new study is reported as a separate, pre-registered study. The current study stays in
  the repository as preliminary work, with its accepted scope.
