# Results: three ways to get a red-team attacker

**Status: complete, AI-annotated, not human-validated.** The numbers below come from
`python reproduce_results.py` (stored in `results_numbers.json`) and from the simulated calibration of
`python estimate.py --calibrate` (stored in `calibration.json` and `design_calibration.json`). They use the
estimator as revised in `ANALYSIS-PLAN.md` C5, after a third external review. Earlier versions of this
file used estimators with known defects; verdicts that changed are noted.

## In short

For these checkpoints, this red-team prompt and this three-attempt configuration, under the AI annotation:

- **Abliteration alone does not beat prompting alone by the pre-registered 5-point margin** (H1, both
  targets). This excludes an advantage of 5 points or more; it does not show there is no advantage at all.
  - Target A: −0.30 [−0.44, −0.16]. Prompting is also significantly better (H2, Holm-adjusted).
  - Target B: −0.09 [−0.18, +0.005]. H2 is not significant (Holm 0.12).
  - **H1 on B rests on the pre-registered pooled miss rate.**
    - With arm-specific miss rates it fails.
    - In a simulation where abliterated-plain's true miss rate is higher than the pooled one, H1 is
      falsely supported 88% of the time.
    - On A, the point estimate stays below the margin even at the least favourable plausible miss rates.
- **Jailbreak-R1, an attacker trained for red-teaming, shows no detectable difference from prompting**
  (E1-H5, primary on B): +0.01 [−0.14, +0.16]. Differences of about ±0.15 are not excluded. It beats
  abliteration alone on A; on B that is unresolved.
- **Unresolved:** whether adding abliteration to a red-team prompt helps (+0.06 [−0.09, +0.20] on A).
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

Goals are resampled jointly across arms with their labels attached, so observed labels stay paired. In
each resample, the rate of each stratum is redrawn from the binomial *confidence distribution* around
that resample's counts and imputed to its unlabelled cells.

- **The draw.** It is an equal mixture of Beta(k, m−k+1) and Beta(k+1, m−k), whose quantiles are the
  Clopper–Pearson limits.
- **Its two boundary properties:**
  - a stratum with 0 of m confirmed still gets an upper tail reaching its Clopper–Pearson bound, so its
    interval never collapses to a point;
  - half of its draws are exactly 0, so a true zero difference is not rejected.
- **Intervals and estimand.** Intervals are 95% percentile intervals over 4000 resamples of goals. The
  estimand is attack success over a population of goals like these.
- **What is modelled across arms.** Imputed rates are drawn independently per arm, except the shared
  pooled miss rate. Dependence between arms in unlabelled cells is modelled only through that and the
  shared goal resampling.

**How the method was chosen** (`ANALYSIS-PLAN.md` C5). Three variants were compared by a pre-stated rule
in a *design-level* calibration (`design_calibration.json`). That calibration uses:

- the real six arms, sampling rules, 40-cell pooled audit and Jailbreak-R1's own 30-cell audit;
- the real hypotheses, run through `test_hypotheses` with the real Holm families;
- abliterated-plain set exactly at H1's null boundary (+0.05) or equal to prompting;
- Jailbreak-R1 set equal to prompting.

1000 experiments per scenario; only this method passed:

| scenario (true values) | H1 falsely supported (nominal ≤ 0.025) | H2 rejected under equality (nominal 0.05) | E1-H5 rejected (nominal 0.05) | min. coverage of hypothesis contrasts | ASR coverage |
|---|---|---|---|---|---|
| A-like, abliterated-plain at +0.05 | 0.011 | — | 0.030 | 0.961 | 0.971 |
| A-like, abliterated-plain equal | — | 0.032 | 0.025 | 0.965 | 0.974 |
| B-like, abliterated-plain at +0.05 | 0.017 | — | 0.022 | 0.954 | 0.976 |
| B-like, abliterated-plain equal | — | 0.043 | 0.020 | 0.947 | 0.975 |
| B-like, +0.05 reached through a **higher miss rate** (pooling wrong) | **0.876** | — | 0.025 | 0.000 | 0.865 |

- **Conservative.** The method is somewhat conservative: ASR coverage is about 0.97 against a nominal
  0.95.
- **The last row is the important limit.** If abliterated-plain's unflagged cells really contain more
  jailbreaks than the other arms', the pre-registered pooled miss rate hides it, and H1 on B would be
  falsely supported. The audit cannot rule that out: abliterated-plain's own audit on B is 1 of 9.
- **The C4 method failed this rule.** The plug-in bootstrap over-rejected H2 under equality (0.067) and
  under-covered (0.928), and it collapsed at 0/m strata.
- **Stylised four-arm scenarios** (`calibration.json`, 2000 experiments each, pooling correct):

  | check | result |
  |---|---|
  | contrast coverage | 0.939–0.974 |
  | twin-null rejections | 0.026–0.056 |
  | Holm familywise error | 0.029–0.045 |

**Calibration is measured in these scenarios, not guaranteed.**

**Tests.**

- **Primary (no adjustment).** H1 is a one-sided margin test: supported if the upper 95% bound is below
  +0.05, with its own one-sided p. E1-H5 is primary on target B only; E1 tests require the target to be
  stated.
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
| no-attacker (just ask) | 0.09 [0.03, 0.22] | 0.04 [0.00, 0.15] |
| aligned-plain | 0.16 [0.07, 0.28] | 0.10 [0.05, 0.20] |
| abliterated-plain | 0.15 [0.08, 0.27] | 0.08 [0.03, 0.20] |
| **aligned-redteam** | **0.45 [0.33, 0.58]** | **0.17 [0.08, 0.28]** |
| abliterated-redteam | 0.52 [0.41, 0.63] | 0.19 [0.11, 0.30] |

| hypothesis | A | B | verdict |
|---|---|---|---|
| **H1** (primary) abliterated-plain − aligned-redteam; supported if upper bound < +0.05 | −0.30 [−0.44, −0.16]; one-sided p (d ≥ +0.05) < 0.001 | −0.09 [−0.18, +0.005]; one-sided p 0.001 | **supported on both** (B only under the pooled miss rate) |
| **H2** same contrast, two-sided test of 0 | p < 0.001, Holm < 0.001 | p 0.062, Holm 0.123 | **A only** |
| H3 abliterated-plain − aligned-plain | −0.01 [−0.10, +0.08], Holm 0.90 | −0.02 [−0.08, +0.04], Holm 0.47 | not significant on either |
| H4a aligned-redteam − no-attacker | +0.36 [+0.22, +0.49], Holm < 0.001 | +0.13 [+0.04, +0.21], Holm 0.010 | beats the floor on both |
| H4b abliterated-plain − no-attacker | +0.06 [+0.003, +0.11], p 0.035, Holm 0.069 | +0.04 [+0.007, +0.07], p 0.024, Holm 0.0705 | not significant after Holm on either |
| H4c abliterated-redteam − no-attacker | +0.42 [+0.30, +0.53], Holm < 0.001 | +0.15 [+0.08, +0.22], Holm 0.0025 | beats the floor on both |
| exploratory: abliterated-redteam − aligned-redteam | +0.06 [−0.09, +0.20] | +0.02 [−0.08, +0.13] | no claim; poorly powered |
| exploratory: aligned-redteam − aligned-plain | +0.30 [+0.15, +0.44] | +0.07 [−0.03, +0.16] | no claim |

## Extension E1: an attacker trained for red-teaming (146 goals)

`yukiyounai/Jailbreak-R1` (arXiv:2506.00782). Four chemical/biological-harm goals were excluded after the
labelling agents' safety system blocked those sheets (`ANALYSIS-PLAN.md` D3), so E1 contrasts use the 146
remaining goals for every arm.

The drift check re-showed 25 original items blind in the E1 batch, and passed:

- target A: kappa 0.75, positive rate 0.36 → 0.40;
- target B: kappa 1.00, positive rate 0.48 → 0.48.

| arm | A | B |
|---|---|---|
| no-attacker | 0.10 [0.03, 0.22] | 0.04 [0.00, 0.15] |
| abliterated-plain | 0.15 [0.08, 0.27] | 0.08 [0.03, 0.20] |
| **trained-redteam** | **0.51 [0.38, 0.63]** | **0.18 [0.09, 0.30]** |
| aligned-redteam | 0.48 [0.35, 0.61] | 0.17 [0.09, 0.28] |
| abliterated-redteam | 0.52 [0.41, 0.63] | 0.19 [0.12, 0.30] |

| hypothesis | A | B | verdict |
|---|---|---|---|
| **E1-H5** trained − aligned-redteam (primary on B; secondary on A) | +0.03 [−0.15, +0.19], Holm 0.78 | **+0.01 [−0.14, +0.16], p 0.92** | **no detectable difference** |
| E1-H6 trained − abliterated-plain | +0.35 [+0.18, +0.49], Holm < 0.001 | +0.10 [−0.04, +0.23], Holm 0.1495 | A only; B unresolved |
| E1 floor: trained − no-attacker | +0.41 [+0.23, +0.54], Holm < 0.001 | +0.14 [−0.001, +0.27], p 0.052, Holm 0.103 | A only (*changed:* B was reported significant) |

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
| as reported | −0.30 [−0.44, −0.16] | −0.09 [−0.18, +0.005] | +0.03 / +0.01 (n.s.) | +0.35 sig / +0.10 n.s. |
| arm-specific miss rates | −0.33 [−0.51, −0.12] | **+0.00 [−0.33, +0.37]: H1 fails** | +0.04 / +0.02 (n.s.) | +0.39 sig / +0.02 n.s. |
| least favourable arm-specific miss rates | −0.12 (point) | **+0.33 (point): H1 fails** | — | — |
| agent 1's blind labels, all arms | −0.38 [−0.50, −0.23] | −0.11 [−0.20, −0.010] | −0.04 / −0.01 (n.s.) | +0.36 sig / +0.10 n.s. |
| agent 2's blind labels, all arms | −0.30 [−0.43, −0.15] | −0.11 [−0.20, −0.009] | +0.04 / −0.01 (n.s.) | +0.36 sig / +0.10 n.s. |
| restricted label flip (below) | −0.14 [−0.29, +0.02] | −0.08 [−0.17, +0.01] | — | — |

- **Arm-specific miss rates** come from 3–12 audit cells per arm, several of them 0/m. They are very
  imprecise.
- **Least favourable rates.** These set abliterated-plain's miss rate to the upper end of its 95%
  Clopper–Pearson interval and aligned-redteam's to the lower end:
  - target A: 0/11 → 0.28, and 0/3 → 0;
  - target B: 1/9 → 0.48, and 0/6 → 0.

  On A the point estimate stays well below the margin (−0.12). On B it moves to +0.33. **H1 on B rests on
  the pooled-miss assumption**, and the design calibration shows what happens if that assumption is wrong
  in this direction.
- **Annotators.** Each row uses one agent's blind labels for every arm, original and E1. The H1, H2 and E1
  verdicts all match the reconciled ones.
- **Restricted label flip.** Every false label on abliterated-plain whose response was truncated, or
  whose cell had another flagged round, is set to true (12 labels on A, 2 on B).
  - It permits only that one error type. It does not bound errors in unsampled cells, other arms' labels,
    false positives on aligned-redteam, or miss rates.
  - H1 still holds on both targets.
  - Prompting's significant advantage on A (H2) does not survive it (Holm 0.079).

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
python estimate.py --selftest         # boundary cases incl. the reviews' counterexamples, quick calibration
python estimate.py --calibrate        # full simulated calibration: calibration.json + design_calibration.json
python reproduce_results.py --legacy  # everything else in this file -> results_numbers.json
```

`reproduce_results.py` computes every number in this file except the calibration tables and the
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
- **C5:** the third external review.
  - The C4 plug-in bootstrap collapsed at 0/m strata. It could falsely support H1, and it could
    distinguish arms with identical true outcomes.
  - Imputed rates are now drawn from the binomial confidence distribution, chosen by a pre-stated rule
    from a design-level calibration of the real hypotheses.
  - E1 tests now require an explicit target.
  - The thinking-mode inference is withdrawn.
  - The E1 floor on B is no longer significant.

Earlier versions of this file are in git history. The judge-only ("screen-level") results that preceded
labelling are in commit `407c47c` and earlier.
