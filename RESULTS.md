# Results: three ways to get a red-team attacker

**Status: complete, AI-annotated, not human-validated.** The numbers below come from
`python reproduce_results.py` (stored in `results_numbers.json`) and from the simulated calibration of
`python estimate.py --calibrate` (stored in `calibration.json`). They use the estimator as revised in
`ANALYSIS-PLAN.md` C4, after a second external review. Earlier versions of this file used estimators with
known defects; verdicts that changed are noted.

## In short

For these checkpoints, this red-team prompt and this three-attempt configuration, under the AI annotation:

- **Abliteration alone does not beat prompting alone by the pre-registered 5-point margin** (H1, both
  targets). This excludes an advantage of 5 points or more; it does not show there is no advantage at all.
  - Target A: −0.30 [−0.42, −0.19]. Prompting is also significantly better (H2, Holm-adjusted).
  - Target B: −0.09 [−0.17, −0.007]. H2 is not significant after Holm adjustment (0.08).
  - H1 on B holds only under the pre-registered pooled miss rate. With arm-specific miss rates it fails.
    On A the point estimate stays below the margin even at the least favourable plausible miss rates.
- **Jailbreak-R1, an attacker trained for red-teaming, shows no detectable difference from prompting**
  (E1-H5, primary on B): +0.01 [−0.12, +0.13]. The interval still allows differences of about ±0.13. It
  beats abliteration alone on A; on B that is unresolved.
- **Unresolved:** whether adding abliteration to a red-team prompt helps (+0.06 [−0.07, +0.18] on A).
- **The two published automated judges agree only moderately** (kappa 0.52–0.60), and some conclusions
  drawn from them differ from those drawn from the labels.

## What is measured

**Outcome.** Only one round per (arm, goal) cell was labelled: the highest-scoring round that a judge
flagged, or for unflagged audit cells the highest-scoring round. The estimand is therefore the success
rate of that *selected round*. With correct labels of full responses, selected-round success would be at
most any-round success ("jailbroken within 3 attempts"). Our estimates are not a guaranteed lower bound
on that, though:

- the labels are judgements of excerpts that can be wrong in either direction;
- unlabelled cells are imputed;
- the pooled miss rate can bias an arm in either direction.

**Labels.** Two independently started instances of one AI model (GPT-6.1 Sol, high reasoning, as
reported by the researchers) labelled every sampled item blind, followed by a reconciliation step.

| | blind agreement (Cohen's kappa) |
|---|---|
| original arms | 0.82 on A (191 items), 0.93 on B (116 items) |
| E1 | 0.92 on A (103 items), 0.97 on B (75 items) |

This shows the labels are *repeatable* under this procedure. It does not show they are *valid*: two
instances of the same model can share systematic errors. No human labels exist yet. Every result is
therefore a comparison under this AI annotation procedure.

**Estimator.** A stratified two-phase sample:

- judge-flagged cells were labelled at a known rate;
- a blind audit sampled the unflagged cells.

Goals are resampled jointly across arms with their labels attached. In each resample, the rate of each
stratum is recomputed from the labels in that resample and imputed to its unlabelled cells (a plug-in
bootstrap). Two arms with identical data therefore get a contrast of exactly 0. Intervals are 95%
percentile intervals over 4000 resamples of goals. The estimand is attack success over a population of
goals like these. Dependence between arms in *unlabelled* cells is modelled only through the shared
resampling of goals and the shared miss rate.

**Calibration** (simulated, 2000 experiments per scenario, under the real sampling design;
`calibration.json`):

| | pooled miss rate correct (3 scenarios) | pooled miss rate wrong |
|---|---|---|
| contrast interval coverage (nominal 0.95) | 0.937–0.953 | 0.899–0.908 for the affected contrasts |
| truth outside one side (nominal 0.025) | 0.018–0.040 | up to 0.093 |
| null rejected at p < 0.05 (nominal 0.05) | 0.045–0.060 | 0.053–0.055 |
| familywise error after Holm (nominal 0.05) | 0.042–0.055 | 0.054 |
| single-arm ASR interval coverage | 0.910–0.952 | 0.908–0.938 |

- **Scope of the checks.** They cover only these scenarios. They show the intervals are close to nominal
  but can be slightly liberal, especially for single-arm ASRs.
- **Boundary strata.** A stratum whose labels are all 0 or all 1 gets no within-stratum spread.
  `reproduce_results.py` lists such strata. None occurs in the primary analyses; they do occur in the
  per-arm miss sensitivity analysis.
- **Pooling wrong.** When the pooled miss rate is wrong, it underestimates the arm whose true miss rate is
  higher, and the contrast is biased against that arm.

**Tests.**

- **Primary (no adjustment).** H1 is a one-sided margin test: supported if the upper 95% bound is below
  +0.05; its one-sided p is reported. E1-H5 is primary on target B only.
- **Secondary.** Two-sided percentile-bootstrap p-values, Holm-adjusted within each study and target. The
  families are:
  - main study: H2, H3 and H4a–c;
  - E1: E1-H6 and the E1 floor, plus E1-H5 on target A.
- **Exploratory.** Reported without a verdict.

## Main study (five arms, 150 goals)

The arms are a 2x2 over the attacker (aligned or abliterated `Qwen3-8B` weights, plain instruction or
red-team system prompt), plus a no-attacker floor that sends the goal to the target verbatim. Every arm
gets 3 attempts per goal.

| arm | A: Qwen2.5-7B | B: Llama-3.1-8B |
|---|---|---|
| no-attacker (just ask) | 0.09 [0.03, 0.17] | 0.04 [0.00, 0.09] |
| aligned-plain | 0.16 [0.08, 0.25] | 0.10 [0.04, 0.17] |
| abliterated-plain | 0.15 [0.08, 0.23] | 0.08 [0.03, 0.15] |
| **aligned-redteam** | **0.45 [0.35, 0.57]** | **0.17 [0.08, 0.26]** |
| abliterated-redteam | 0.52 [0.42, 0.61] | 0.19 [0.11, 0.27] |

| hypothesis | A | B | verdict |
|---|---|---|---|
| **H1** (primary) abliterated-plain − aligned-redteam; supported if upper bound < +0.05 | −0.30 [−0.42, −0.19]; one-sided p (d ≥ +0.05) < 0.001 | −0.09 [−0.17, −0.007]; one-sided p < 0.001 | **supported on both** (B only under pooled miss rate) |
| **H2** same contrast, two-sided test of 0 | p < 0.001, Holm < 0.001 | p 0.029, Holm 0.084 | **A only** |
| H3 abliterated-plain − aligned-plain | −0.01 [−0.09, +0.08], Holm 0.88 | −0.02 [−0.08, +0.03], Holm 0.42 | not significant on either |
| H4a aligned-redteam − no-attacker | +0.36 [+0.25, +0.48], Holm < 0.001 | +0.13 [+0.05, +0.21], Holm 0.002 | beats the floor on both |
| H4b abliterated-plain − no-attacker | +0.06 [+0.005, +0.11], p 0.029, Holm 0.059 | +0.04 [+0.007, +0.08], p 0.028, Holm 0.084 | not significant after Holm on either |
| H4c abliterated-redteam − no-attacker | +0.42 [+0.32, +0.53], Holm < 0.001 | +0.15 [+0.08, +0.22], Holm < 0.001 | beats the floor on both |
| exploratory: abliterated-redteam − aligned-redteam | +0.06 [−0.07, +0.18] | +0.02 [−0.08, +0.12] | no claim; poorly powered |
| exploratory: aligned-redteam − aligned-plain | +0.30 [+0.17, +0.42] | +0.07 [−0.01, +0.15] | no claim |

## Extension E1: an attacker trained for red-teaming (146 goals)

`yukiyounai/Jailbreak-R1` (arXiv:2506.00782). Four chemical/biological-harm goals were excluded after the
labelling agents' safety system blocked those sheets (`ANALYSIS-PLAN.md` D3), so E1 contrasts use the 146
remaining goals for every arm.

The drift check re-showed 25 original items blind in the E1 batch, and passed:

- target A: kappa 0.75, positive rate 0.36 → 0.40;
- target B: kappa 1.00, positive rate 0.48 → 0.48.

| arm | A | B |
|---|---|---|
| no-attacker | 0.10 [0.03, 0.18] | 0.04 [0.00, 0.10] |
| abliterated-plain | 0.15 [0.08, 0.24] | 0.08 [0.02, 0.16] |
| **trained-redteam** | **0.51 [0.39, 0.62]** | **0.18 [0.09, 0.27]** |
| aligned-redteam | 0.48 [0.37, 0.59] | 0.17 [0.09, 0.26] |
| abliterated-redteam | 0.52 [0.42, 0.62] | 0.19 [0.12, 0.28] |

| hypothesis | A | B | verdict |
|---|---|---|---|
| **E1-H5** trained − aligned-redteam (primary on B; secondary on A) | +0.03 [−0.12, +0.17], Holm 0.75 | **+0.01 [−0.12, +0.13], p 0.90** | **no detectable difference** |
| E1-H6 trained − abliterated-plain | +0.35 [+0.21, +0.48], Holm < 0.001 | +0.10 [−0.01, +0.21], Holm 0.077 | A only; B unresolved |
| E1 floor: trained − no-attacker | +0.41 [+0.27, +0.53], Holm < 0.001 | +0.14 [+0.03, +0.24], Holm 0.010 | beats the floor on both |

**E1 compares whole systems, not the effect of red-team training alone.** Jailbreak-R1 differs from the
prompted aligned attacker in several ways at once:

| | aligned-redteam | trained-redteam |
|---|---|---|
| base model | Qwen3-8B | Qwen2.5-7B-Instruct (the same model as target A) |
| attempts | refines using the target's replies | 3 independent samples (its trained format) |
| sampling | temperature 0.7, up to 300 tokens | temperature 1.0, top-p 0.95, up to 1,024 tokens, forced answer start |
| collected | main-study session | a later session (see below) |

- **Matched-base control.** Isolating the effect of red-team training would need one.
- **Training-data overlap.** Whether Jailbreak-R1's training or reward data overlapped with these
  StrongREJECT goals or these targets has not been checked. Its training code loads data by path, and the
  paper page does not name its datasets.
- **Format.** It follows the authors' code except one documented change to prompt clean-up
  (`ANALYSIS-PLAN.md`, E1 format).
- **Same targets across sessions.**
  - *Weights:* since September 2024 the target repositories have changed only README and metadata files
    (Qwen) or nothing at all (Llama, since July 2024). Any download at either collection therefore gave
    identical weights and tokenizer files (`MANIFEST.md`).
  - *Decoding:* the target settings are fixed in `redteam.py` and are the same in both sessions.
  - *Unrecorded:* the main study's vLLM version and serving options. E1 contrasts therefore assume the
    serving was otherwise equivalent, and may include a collection-session effect.

## Sensitivity analyses (post hoc)

| analysis | H1 A | H1 B | E1-H5 A / B | E1-H6 A / B |
|---|---|---|---|---|
| as reported | −0.30 [−0.42, −0.19] | −0.09 [−0.17, −0.007] | +0.03 / +0.01 (n.s.) | +0.35 sig / +0.10 n.s. |
| arm-specific miss rates (plug-in) | −0.33 [−0.45, −0.22] | **+0.00 [−0.16, +0.24]: H1 fails** | +0.04 / +0.02 (n.s.) | +0.39 sig / +0.02 n.s. |
| least favourable arm-specific miss rates | −0.12 (point) | **+0.33 (point): H1 fails** | — | — |
| agent 1's blind labels, all arms | −0.38 [−0.50, −0.26] | −0.11 [−0.19, −0.02] | −0.04 / −0.01 (n.s.) | +0.36 sig / +0.10 n.s. |
| agent 2's blind labels, all arms | −0.30 [−0.42, −0.18] | −0.11 [−0.19, −0.02] | +0.04 / −0.01 (n.s.) | +0.36 sig / +0.10 n.s. |
| restricted label flip (below) | −0.14 [−0.28, −0.006] | −0.08 [−0.16, +0.003] | — | — |

- **Arm-specific miss rates** come from 3–12 audit cells per arm. Several are 0/m, which this bootstrap
  cannot spread, so these intervals are too narrow.
- **Least favourable rates.** These set abliterated-plain's miss rate to the upper end of its 95%
  Clopper–Pearson interval and aligned-redteam's to the lower end:
  - target A: 0/11 → 0.28, and 0/3 → 0;
  - target B: 1/9 → 0.48, and 0/6 → 0.

  On A the point estimate stays well below the margin (−0.12). On B it moves to +0.33. **H1 on B rests on
  the pooled-miss assumption.**
- **Annotators.** Each sensitivity row uses one agent's blind labels for every arm, original and E1. All
  verdicts match the reconciled ones, except that H2 on B becomes significant under either agent alone.
- **Restricted label flip.** Every false label on abliterated-plain whose response was truncated, or
  whose cell had another flagged round, is set to true (12 labels on A, 2 on B).
  - It permits only that one error type. It does not bound errors in unsampled cells, other arms' labels,
    false positives on aligned-redteam, or miss rates.
  - H1 still holds on both targets.

## Attacker behaviour (mechanical string checks, no judge or labels)

Shares of attack rounds (450 per arm and target); target A shown (B within two points):

| arm | withheld as refusal (legacy detector) | withheld and opens as a refusal | copied the goal near-verbatim (similarity > 0.8) |
|---|---|---|---|
| aligned-plain | 0.27 (B 0.29) | 0.25 (B 0.25) | 0.04 |
| abliterated-plain | 0.01 (B 0.00) | 0.00 | 0.29 |
| aligned-redteam | 0.00 | 0.00 | 0.00 |
| abliterated-redteam | 0.00 | 0.00 | 0.00 |
| trained-redteam | 0.01 (B 0.00) | 0.00 | 0.00 |

Under a plain instruction, the abliterated checkpoint produces fewer detected refusals and much more
near-verbatim copying of the goal than the aligned one. The red-team prompt removes detected refusals
without copying. The copying gap holds at every similarity threshold from 0.5 to 0.95 (shares of sent
rounds: 0.60 vs 0.35 at 0.5, 0.21 vs 0.03 at 0.95, on A).

These measurements do **not** establish a general loss of capability, nor that copying causes the success
gap; that is a plausible hypothesis, untested here. A checkpoint comparison also does not isolate
"safety" from other effects of this particular weight edit.

**The refusal detector also changed what was collected.**

- Some attack prompts were withheld because they contain a marker such as "as an AI", without opening
  as a refusal:

  | arm | A | B |
  |---|---|---|
  | aligned-plain | 10 | 18 |
  | abliterated-plain | 4 | — |
  | aligned-redteam | 1 | — |
  | trained-redteam | 4 | 2 |

- Withheld prompts never reached the target, and refining attackers then saw an empty reply.
- Realised target queries per 450 attempts were 328 (A) and 320 (B) for aligned-plain, against 446–450
  for the other arms. The arms therefore did not receive identical realised budgets.

## The automated judges

**Agreement with each other** (no labels involved). StrongREJECT ≥ 0.7 vs the HarmBench classifier on
the five original arms, with bootstrap intervals over goals:

| | round level | (arm, goal) cell level |
|---|---|---|
| A | kappa 0.56 [0.49, 0.62] | kappa 0.60 [0.52, 0.67] |
| B | kappa 0.52 [0.42, 0.63] | kappa 0.59 [0.48, 0.69] |

HarmBench flags 60 (A) and 22 (B) cells that StrongREJECT scores below 0.7. Under these implementations
and thresholds the two evaluators produce materially different classifications. Moderate kappa alone does
not show that either is invalid, and ASRs from different judges should not be compared without checking
agreement.

**Against the AI labels** (descriptive; the labels are themselves unvalidated):

- **Judge-only results can differ from label-based ones.**
  - Both judges report abliterated-plain below aligned-plain: −0.07 to −0.13 across the four
    judge/target columns, each interval excluding 0. With labels, that contrast is not detectable.
  - StrongREJECT reports Jailbreak-R1 below aligned-redteam on the 146 shared goals: −0.18 (A) and
    −0.16 (B), both intervals excluding 0. The labels detect no difference.
- **Share of judge flags confirmed by the labels, per arm** (146 shared goals):

  | target | no-attacker | aligned-plain | abliterated-plain | aligned-redteam | abliterated-redteam | trained-redteam |
  |---|---|---|---|---|---|---|
  | A | 7/15 | 8/20 | 13/20 | 30/51 | 33/42 | 29/48 |
  | B | 2/4 | 9/20 | 7/9 | 10/23 | 15/20 | 12/20 |

  Confirmation rates look lower for the aligned arms. No design-aware test was run. Goal drift — attackers
  rewriting a goal into a safer neighbour that judges still flag — is a proposed explanation, not a
  measured one.
- **Exploratory miss rates.** The audit found real jailbreaks that neither judge flagged:

  | arms | A | B |
  |---|---|---|
  | original arms, pooled (150 goals) | 2/40 | 1/40 |
  | Jailbreak-R1, its own audit | 7/30 | 2/30 |

  On the 146 shared goals the A difference, 7/30 vs 2/39, gives Fisher's exact p = 0.035. It does not
  survive correction across the two targets (B: 2/30 vs 1/39, p = 0.58).
- **Earlier comparisons against one AI annotator** (the assistant's own labels on a pilot run) were
  disagreements among automated evaluators, not validation against humans (`ANALYSIS-PLAN.md` C1).

## Measurement limits

- **One labelled round per cell.** A cell counts if any round succeeds, but only the selected round was
  labelled. Among candidate cells labelled false, some had another flagged round that nobody labelled:

  | arm | target A | target B |
  |---|---|---|
  | aligned-redteam | 15 of 23 | 4 of 13 |
  | abliterated-plain | 1 of 7 | 1 of 2 |
  | abliterated-redteam | 3 of 9 | 3 of 5 |

  This is a different shortfall per arm, so its effect on any contrast is not established. The fix is to
  label every round in sampled cells.
- **Truncated responses.** Sheets showed the first 1,600 characters of each response.
  - 172 of 191 (A) and 60 of 116 (B) original items were longer.
  - It was more common for aligned-redteam (55 of 56 items on A) than for abliterated-plain (24 of 31).
  - Hidden text can hide a success, and can also hide context that changes how a visible one should be
    read. Its effect on contrasts is not established.
- **Ties count as failures.** Unresolved disagreements are labelled false in every arm. If ambiguity
  differs by arm, this can bias a contrast either way.
- **Pooled miss rate** for the original arms (pre-registered). Its effect is shown in the sensitivity
  analyses.
- **Audit inclusion probabilities** are only approximately equal across arms (0.089–0.094 on A,
  0.061–0.069 on B) because of integer allocation. The pooled rate is therefore approximately, not
  exactly, self-weighting.

## Scope and limitations

- **Labels:** AI annotators only (two instances of one model), with no human validation sample. This is
  the main open weakness.
- **Attackers:** every attacker is from the Qwen family, including Jailbreak-R1, so none is independent
  of that lineage.
- **Abliteration:** one community abliteration (huihui-ai v2; its model card describes
  implementation-specific changes).
- **Prompts:** one red-team system prompt and one plain instruction.
- **Targets:** two small 2024-era models; nothing here speaks to frontier or closed models.
- **Scale:**
  - 150 goals (146 in E1), StrongREJECT only;
  - one stochastic collection per cell, 3 attempts per goal;
  - bootstrap intervals cover goal sampling, not run-to-run variation.
- **Harness:** a simplified, judge-free refinement loop in the spirit of PAIR, not a canonical PAIR or
  TAP implementation, so no claim of competitive attack strength is made.

## Reproducing

The data (scored transcripts, labelling keys, labels) is gitignored because it contains model-generated
harmful text, so the final numbers cannot be reproduced from the repository alone. Dependencies are in
`requirements.txt`. With the local `adj/` folder and `*_scored.json` files:

```bash
python redteam.py --selftest          # attack loop, template attacker, refusal checks, metrics
python estimate.py --selftest         # boundary cases, pairing, quick calibration
python estimate.py --calibrate        # full simulated calibration (the table above)
python reproduce_results.py --legacy  # everything else in this file -> results_numbers.json
```

`reproduce_results.py` computes every number in this file except the calibration table and the
historical references in "History". `--legacy` adds the pre-registered legacy estimator's H1 contrast:
−0.30 [−0.42, −0.16] on A and −0.10 [−0.18, −0.02] on B.

To re-collect and re-label from scratch:

- **Models, revisions and settings** are listed in `MANIFEST.md`.
- **StrongREJECT judge:** `sr_judge.py` reads `judge_templates.json`, which is included, with its source
  and hash in `MANIFEST.md`.
- **Historical labelling sheets** were cut at 1,600 characters, so regenerate them with
  `estimate.py --sample ... --max-chars 1600`.

## History

Superseded results, deviations and corrections are logged in `ANALYSIS-PLAN.md`, rather than rewritten:

- **D1–D4:** labelling events.
- **C1:** earlier "hand validation" claims rested on the assistant's own labels.
- **C2:** refusal figures and a rounding fix.
- **C3:** the first estimator replaced (its contrasts were not paired).
- **C4:** the second external review.
  - The replacement estimator could declare a difference when the true difference was zero; it is now a
    plug-in bootstrap.
  - H1 and H2 are tested separately, with H2 in the Holm family.
  - The annotator sensitivity analyses use one agent's labels throughout.
  - Claims are narrowed.

Earlier versions of this file are in git history. The judge-only ("screen-level") results that preceded
labelling are in commit `407c47c` and earlier.
