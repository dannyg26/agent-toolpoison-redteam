# How should you get a red-team attacker? Prompting vs. abliteration vs. a trained attacker

## The question
An automated **red-team agent** is an AI that attacks a target model to find its safety holes. A useful
attacker has to be *willing* to write attacks, and there are three common ways to get one:

1. **prompt** an aligned model with a red-team system prompt;
2. **abliterate** it — a weight edit that removes the refusal direction (Arditi et al. 2024); or
3. download a model **trained** for red-teaming (here Jailbreak-R1, arXiv:2506.00782).

This study compares these attacker *configurations* against the same targets, goals and query budget.
It measures attack success and simple attacker behaviours (detected refusal, near-verbatim copying of
the goal). It does **not** measure general capability, and it does not isolate "safety" from every
other consequence of a particular weight edit or training run.

## Why this project
- **Red-team agents** are the subject itself (the advisor's requirement).
- **Abliterated models** are one of the attacker conditions.
- **Defensive measurement** with standard benchmark goals. Generated text stays in local, gitignored
  files.

## Related work and the gap
- **Automated red-teaming with an attacker LLM:** PAIR (Chao et al. 2023, arXiv:2310.08419) and TAP
  (Mehrotra et al. 2023, arXiv:2312.02119); agentic variants such as CoP (arXiv:2506.00781).
- **Benchmarks and evaluators:** HarmBench (Mazeika et al. 2024, arXiv:2402.04249) and StrongREJECT
  (Souly et al. 2024, arXiv:2402.10260), whose goals and fine-tuned judge we use.
- **Attackers and refusal.**
  - J2 (arXiv:2502.09638) notes that refusal training leads strong LLMs to refuse to help with
    jailbreaking, and shows that prompted frontier models can nonetheless act as attackers.
  - Self-improved red teaming (arXiv:2610.34965) reports that awareness of the adversarial objective
    causes explicit refusal and non-refusal "sandbagging" in attacker roles.
  - Jailbreak-R1 (arXiv:2506.00782) trains an attacker with reinforcement learning.
- **Abliteration:** Arditi et al. 2024 (arXiv:2406.11717).
- **Judge reliability:** "How Reliable Is Your Jailbreak Judge?" (arXiv:2606.25487) and "An Empirical
  Measurement of Jailbreaking Evaluators" (arXiv:2609.10594) study evaluator calibration and
  disagreement. Our evaluator results add a measurement on attacker-generated transcripts, but they are
  relative to an unvalidated AI annotation.

**Gap, to our knowledge.** Searches of arXiv and the web in November 2026 found no controlled comparison
that holds target, goals, budget and scoring fixed while varying *how the attacker is made willing* —
prompting, abliteration, or red-team training. This is a bounded claim, not proof that none exists.

## Design
Main study: a 2x2 over the attacker, plus a floor.

|  | plain instruction | red-team system prompt |
|---|---|---|
| **aligned weights** (`Qwen/Qwen3-8B`) | `aligned-plain` | `aligned-redteam` |
| **abliterated weights** (`huihui-ai/Huihui-Qwen3-8B-abliterated-v2`) | `abliterated-plain` | `abliterated-redteam` |

Plus **`no-attacker`**, which sends the goal to the target verbatim, re-sampled for the same number of
attempts. Extension **E1** adds `trained-redteam` (`yukiyounai/Jailbreak-R1`), run in its authors' format
(`attackers/jailbreak_r1.json`). E1 is a system-level comparison: its base model, attempt structure and
decoding differ from the other arms (see `RESULTS.md`).

**Attack loop** (simplified, PAIR-style, judge-free):

1. The attacker writes a prompt for the goal.
2. The target answers.
3. If attempts remain, a refining attacker sees the reply and writes a new prompt. Jailbreak-R1 instead
   draws independent samples, because it was trained single-shot.
4. Every arm uses its full **3 attempts**; nothing is judged during collection.

An attacker output that the refusal detector flags is not sent to the target. The legacy detector also
flags some genuine attack prompts; the effect is reported in `RESULTS.md`.

**Targets and goals.**

- Target A: `Qwen/Qwen2.5-7B-Instruct`.
- Target B: `NousResearch/Meta-Llama-3.1-8B-Instruct`, a second target family.
- Goals: 150 StrongREJECT behaviours; 146 in E1, after excluding 4 chemical/biological-harm goals
  (`ANALYSIS-PLAN.md` D3).
- The HarmBench and AdvBench *datasets* are wired up and unused; the HarmBench *classifier* is used for
  scoring.

**Scoring, after collection.**

1. Two judges score every round: the HarmBench classifier and the StrongREJECT fine-tuned judge.
2. A stratified sample is drawn: cells either judge flagged, plus a blind audit of unflagged cells.
3. Two independently started AI agents label it, with the rule in `LABELING-PROTOCOL.md` (operative
   procedure).
4. `estimate.py` estimates attack success with a goal-level two-phase bootstrap.

The labelled outcome is the success of one selected round per (arm, goal) cell, a lower bound on
"jailbroken within 3 attempts".

## Answer (AI-annotated, not human-validated)

For these checkpoints, this prompt and this configuration (details and intervals in `RESULTS.md`):

- **Abliteration is not better than prompting** (pre-registered H1, both targets).
  - It is significantly worse on target A (−0.30 [−0.43, −0.16]).
  - On target B (−0.09 [−0.18, +0.005]) it is not significantly worse.
  - H1 on target B depends on the pooled miss-rate assumption.
- **The trained attacker is not detectably different from prompting** (E1-H5): +0.01 [−0.13, +0.16]
  on target B. It beats abliteration on target A; on B that is unresolved.
- **Under a plain instruction, the abliterated checkpoint shows** fewer detected refusals and much more
  near-verbatim goal copying than the aligned one, with no detectable difference in attack success.
- **Whether abliteration adds anything on top of a good prompt** is unresolved; the study is poorly
  powered for the effects simulated.

## Where it stands
- ✅ Collection, both judges and the AI-agent labelling are complete for the five main arms and E1;
  `python reproduce_results.py` recomputes every reported number.
- ✅ An analysis plan was frozen *after* collection and automated scoring, but *before* the agent
  labels used for the estimates (`ANALYSIS-PLAN.md`, including the chronology in C3).
- ✅ Deviations (D1–D4) and corrections (C1–C3) are logged. C3 replaced an estimator whose contrasts
  were not truly paired, after an external review; one verdict changed (H2 on target B).
- ⏳ **Open, in priority order:**
  1. a blinded human validation sample of the AI labels (the main weakness);
  2. labelling every round in sampled cells, with full responses;
  3. a non-Qwen attacker family;
  4. more goals and repeated collections;
  5. more than one red-team prompt;
  6. an audit of Jailbreak-R1's training-data overlap.

Files:

- **collection:** `redteam.py`
- **scoring:** `rescore.py`, `sr_judge.py`
- **sampling and estimates:** `estimate.py`
- **every reported number:** `reproduce_results.py`
- **aggregates and judge agreement:** `summarize.py`
- **annotator agreement:** `adjudicate.py`
- **legacy screened-only sheets:** `analyze.py`
- **models, revisions and settings:** `MANIFEST.md`
