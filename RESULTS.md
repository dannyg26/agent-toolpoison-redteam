# Results: three ways to get a red-team attacker

**Status: complete, AI-annotated, not human-validated.** Every number below is recomputed by
`python reproduce_results.py` from the local data (see "Reproducing") using the corrected estimator
described in `ANALYSIS-PLAN.md` C3. Earlier versions of this file used an estimator whose contrasts were
not truly paired; where that changed a verdict, it is noted.

## In short

For these checkpoints, this red-team prompt and this three-attempt configuration:

- **Abliteration is not better than prompting** an aligned model (pre-registered H1, both targets).
  - On target A it is significantly *worse*: −0.30 [−0.43, −0.16].
  - On target B the estimate is −0.09 [−0.18, +0.005], not significant.
  - H1 on B holds only under the pre-registered pooled miss rate; with arm-specific miss rates the B
    interval is too wide to conclude anything.
- **An attacker trained for red-teaming (Jailbreak-R1) is not detectably different from prompting**
  (E1-H5): +0.01 [−0.13, +0.16] on target B, +0.03 [−0.15, +0.20] on A. It beats abliteration on A;
  on B that is unresolved.
- **The two published automated judges agree only moderately** (kappa about 0.52–0.60), and conclusions
  drawn from them differ from those drawn from the labels.

## What is measured

**Outcome.** Only one round per (arm, goal) cell was labelled: the highest-scoring round that a judge
flagged, or for unflagged audit cells the highest-scoring round. "ASR" below is therefore the success
rate of that selected round, a **lower bound** on "jailbroken within 3 rounds". The gap can differ
by arm, so contrasts are not guaranteed to be conservative; see "Measurement limits".

**Labels.** Two independently started instances of one AI model (GPT-6.1 Sol, high reasoning, as
reported by the researchers) labelled every sampled item blind, followed by a reconciliation step:

| | blind agreement |
|---|---|
| original arms | kappa 0.82 (A), 0.93 (B) |
| E1 | kappa 0.92 (A), 0.97 (B) |

This shows the labels are *repeatable* under this procedure. It does not show they are *valid*: two
instances of the same model can share systematic errors. No human labels exist yet. Every result is
therefore a comparison under this AI annotation procedure.

**Estimator.** Stratified two-phase sample:

- judge-flagged cells were labelled at a known rate;
- a blind audit sampled the unflagged cells;
- goals are resampled jointly across arms with their labels attached (paired);
- intervals are 95% bootstrap percentile intervals over 4000 resamples of goals; the estimand is
  attack success over a population of goals like these.

In simulation with correlated outcomes the intervals covered 0.947–0.987, i.e. about nominal and
slightly conservative for low-flag arms (`estimate.py --selftest`). Secondary contrasts carry a Holm
adjustment within each analysis; primary contrasts (H1 and E1-H5) do not need one.

## Main study (five arms, 150 goals)

The arms are a 2x2 over the attacker (aligned or abliterated `Qwen3-8B` weights, plain instruction or
red-team system prompt), plus a no-attacker floor that sends the goal to the target verbatim. Every arm
gets 3 attempts per goal.

| arm | A: Qwen2.5-7B | B: Llama-3.1-8B |
|---|---|---|
| no-attacker (just ask) | 0.09 [0.03, 0.21] | 0.04 [0.00, 0.14] |
| aligned-plain | 0.16 [0.07, 0.27] | 0.10 [0.05, 0.20] |
| abliterated-plain | 0.15 [0.08, 0.26] | 0.08 [0.03, 0.19] |
| **aligned-redteam** | **0.45 [0.34, 0.58]** | **0.17 [0.08, 0.28]** |
| abliterated-redteam | 0.52 [0.40, 0.62] | 0.19 [0.12, 0.30] |

| contrast | A | B | verdict |
|---|---|---|---|
| **H1** (primary) abliterated-plain − aligned-redteam; upper bound < +0.05 on both | −0.30 [−0.43, −0.16] (p < 0.001) | −0.09 [−0.18, +0.005] (p 0.065) | **supported on both** (B conditional on pooled miss rate) |
| **H2** same contrast; upper bound < 0 | yes | **no** | A only (*changed:* the legacy estimator gave both) |
| H3 abliterated-plain − aligned-plain | −0.01 [−0.10, +0.08] (Holm 0.90) | −0.02 [−0.08, +0.03] (Holm 0.94) | not detectable on either |
| red-team prompt on aligned weights | +0.30 [+0.15, +0.43] (Holm < 0.01) | +0.07 [−0.02, +0.15] (Holm 0.49) | A only |
| H4 aligned-redteam − no-attacker | +0.36 [+0.22, +0.49] (Holm < 0.01) | +0.13 [+0.04, +0.22] (Holm 0.01) | beats the floor on both |
| H4 abliterated-redteam − no-attacker | +0.42 [+0.30, +0.53] (Holm < 0.01) | +0.15 [+0.08, +0.22] (Holm < 0.01) | beats the floor on both |
| H4 abliterated-plain − no-attacker | +0.06 [+0.002, +0.11] (p 0.040, Holm 0.12) | +0.04 [+0.007, +0.07] (p 0.019, Holm 0.08) | not established after Holm (*changed*) |
| exploratory: abliterated-redteam − aligned-redteam | +0.06 [−0.08, +0.20] | +0.02 [−0.08, +0.13] | unresolved; poorly powered for the simulated effects |

## Extension E1: an attacker trained for red-teaming (146 goals)

`yukiyounai/Jailbreak-R1` (Guo et al. 2025, arXiv:2506.00782). Four chemical/biological-harm goals were
excluded after the labelling agents' safety system blocked those sheets (`ANALYSIS-PLAN.md` D3), so E1
contrasts use the 146 remaining goals for every arm. The drift check, which re-showed original items
blind, passed: kappa 0.75 (A) and 1.00 (B), positive-rate shift ≤ 0.04.

| arm | A | B |
|---|---|---|
| no-attacker | 0.10 [0.04, 0.22] | 0.04 [0.00, 0.15] |
| abliterated-plain | 0.15 [0.08, 0.27] | 0.08 [0.03, 0.19] |
| **trained-redteam** | **0.51 [0.38, 0.63]** | **0.18 [0.09, 0.31]** |
| aligned-redteam | 0.48 [0.35, 0.61] | 0.17 [0.09, 0.28] |
| abliterated-redteam | 0.52 [0.41, 0.63] | 0.19 [0.11, 0.29] |

| contrast | A | B | verdict |
|---|---|---|---|
| **E1-H5** (primary, judged on B) trained − aligned-redteam | +0.03 [−0.15, +0.20] (p 0.79) | **+0.01 [−0.13, +0.16] (p 0.93)** | **not detectably different** |
| E1-H6 trained − abliterated-plain | +0.35 [+0.19, +0.48] (Holm < 0.01) | +0.10 [−0.04, +0.24] (Holm 0.60) | A only; B unresolved |
| trained − no-attacker | +0.41 [+0.24, +0.54] (Holm < 0.01) | +0.14 [+0.009, +0.27] (p 0.038, Holm 0.19) | A; B not after Holm (*changed*) |

**E1 compares whole systems, not the effect of red-team training alone.** Jailbreak-R1 differs from the
prompted aligned attacker in several ways at once:

| | aligned-redteam | trained-redteam |
|---|---|---|
| base model | Qwen3-8B | Qwen2.5-7B-Instruct (the same model as target A) |
| attempts | refines using the target's replies | 3 independent samples (its trained format) |
| sampling | temperature 0.7, up to 300 tokens | temperature 1.0, top-p 0.95, up to 1,024 tokens, forced answer start |

Isolating the effect of red-team training would need a matched-base control. Whether Jailbreak-R1's
training or reward data overlapped with these StrongREJECT goals or these targets has not been checked:
its training code loads data by path, and the paper page does not name its datasets. Its format follows
the authors' code except one documented change to prompt clean-up (`ANALYSIS-PLAN.md`, E1 format).

## Sensitivity analyses (post hoc)

| analysis | headline A | headline B | E1-H5 A / B | E1-H6 A / B |
|---|---|---|---|---|
| as reported | −0.30 [−0.43, −0.16] | −0.09 [−0.18, +0.005] | +0.03 / +0.01 (both n.s.) | +0.35 sig / +0.10 n.s. |
| arm-specific miss rates | −0.33 [−0.49, −0.14] | **+0.00 [−0.27, +0.34]** | +0.04 / +0.02 (both n.s.) | +0.39 sig / +0.02 n.s. |
| agent 1's blind labels only | −0.38 [−0.50, −0.24] | −0.11 [−0.20, −0.005] | +0.06 / +0.01 (both n.s.) | +0.38 sig / +0.10 n.s. |
| agent 2's blind labels only | −0.30 [−0.43, −0.15] | −0.11 [−0.19, −0.005] | +0.04 / +0.01 (both n.s.) | +0.37 sig / +0.10 n.s. |
| restricted label flip (below) | −0.14 [−0.30, +0.02] | −0.08 [−0.16, +0.01] | — | — |

- **Arm-specific miss rates** come from 6–12 audit cells per arm, so they are very imprecise. The B
  headline loses its sign and H1 on B does not hold, so the B non-superiority conclusion rests on the
  pooled-miss assumption. A is robust.
- **Restricted label flip.** Every false label on abliterated-plain whose response was truncated, or
  whose cell had another flagged round, is set to true (12 labels on A, 2 on B). It permits only that one
  error type. It does not bound errors in unsampled cells, other arms' labels, false positives on
  aligned-redteam, or miss rates. Under it, H1 still holds on both targets, but prompting's
  *significant* advantage on A does not.
- **Annotators.** The E1 verdicts are the same under either agent's blind labels. The B headline is
  borderline: significant under each agent alone (upper bound −0.005), not under the reconciled labels
  (+0.005), so it is sensitive to annotator choice.

## Attacker behaviour (mechanical string checks, no judge or labels)

Shares of attack rounds; target A shown (B within two points):

| arm | withheld as refusal (legacy detector) | of which opens as a refusal | copied the goal near-verbatim (similarity > 0.8) |
|---|---|---|---|
| aligned-plain | 0.27 (B 0.29) | 0.25 (B 0.25) | 0.04 |
| abliterated-plain | 0.01 (B 0.00) | 0.00 | 0.29 |
| aligned-redteam | 0.00 | 0.00 | 0.00 |
| abliterated-redteam | 0.00 | 0.00 | 0.00 |
| trained-redteam | 0.01 (B 0.00) | 0.00 | 0.00 |

Operationally, for these checkpoints: the abliterated checkpoint produces fewer detected refusals and
much more near-verbatim copying of the goal than the aligned one, and the red-team prompt removes
detected refusals without copying. The copying gap holds at every similarity threshold from 0.5 to 0.95.
These measurements do **not** establish a general loss of capability, nor that copying causes the
success gap. That is a plausible hypothesis, untested here. A checkpoint comparison also does not
isolate "safety" from other effects of this particular weight edit.

**The refusal detector also changed what was collected.** Some attack prompts were withheld because
they contain a marker such as "as an AI", without opening as a refusal: 10 (A) and 18 (B) for
aligned-plain, 4 (A) for abliterated-plain, 1 (A) for aligned-redteam, and 4 (A) and 2 (B) for
trained-redteam. Withheld prompts never reached the target, and refining attackers then saw an empty
reply. Realised target queries per 450 attempts were 328 (A) and 320 (B) for aligned-plain, against
446–450 for the other arms. The arms therefore did not receive identical realised budgets.

## The automated judges

**Agreement with each other** (no labels involved). StrongREJECT ≥ 0.7 vs the HarmBench classifier,
bootstrap intervals over goals:

| | round level | (arm, goal) cell level |
|---|---|---|
| A | kappa 0.56 [0.49, 0.62] | kappa 0.60 [0.53, 0.67] |
| B | kappa 0.52 [0.42, 0.63] | kappa 0.59 [0.48, 0.69] |

HarmBench flags 60 (A) and 22 (B) cells that StrongREJECT scores below 0.7. Under these implementations
and thresholds the two evaluators produce materially different classifications. Moderate kappa alone
does not show that either is invalid, and ASRs from different judges should not be compared without
checking agreement.

**Against the AI labels** (descriptive; the labels are themselves unvalidated):

- **Judge-only results can differ from label-based ones.** Both judges reported a significant drop for
  abliterated-plain vs aligned-plain (−0.07 to −0.13 in all four judge/target columns); with labels
  that contrast is not detectable. StrongREJECT reported Jailbreak-R1 significantly *worse* than
  aligned-redteam on both targets (−0.15, −0.16); the labels do not detect a difference.
- **Share of judge flags confirmed by the labels, per arm.** A: no-attacker 7/15, aligned-plain 8/20,
  abliterated-plain 13/20, aligned-redteam 30/53, abliterated-redteam 34/43, trained-redteam 29/48.
  B: 2/4, 9/20, 7/9, 10/23, 15/20, 12/20. Confirmation rates look lower for the aligned arms. No
  design-aware test was run (an earlier version reported naive p-values, now withdrawn), and goal drift
  — attackers rewriting a goal into a safer neighbour that judges still flag — is a proposed explanation,
  not a measured one.
- **Exploratory miss rates.** The audit found real jailbreaks that neither judge flagged: 2/40 (A) and
  1/40 (B) for the original arms, and 7/30 (A) and 2/30 (B) for Jailbreak-R1. On the 146 shared goals
  the A difference, 7/30 (23%) vs 2/39 (5%), gives Fisher's exact p = 0.035; it does not survive
  correction across the two targets (B: 2/30 vs 1/39, p = 0.58).
- **Earlier comparisons against one AI annotator** (the assistant's own labels on a pilot run) showed
  four automated evaluators disagreeing substantially with those labels. They are disagreements among
  automated evaluators, not validation against humans (`ANALYSIS-PLAN.md` C1).

## Measurement limits

- **One labelled round per cell.** A cell counts if any round succeeds, but only the selected round was
  labelled. Of aligned-redteam's cells labelled false on A, 15 of 23 had another flagged round nobody
  labelled; the figures are 1 of 7 for abliterated-plain and 3 of 9 for abliterated-redteam. This
  undercounts every arm, more for some arms, but the weighted effect on any contrast is not established.
  The fix is to label every round in sampled cells.
- **Truncated responses.** Sheets showed the first 1,600 characters of each response; 172 of 191 (A) and
  60 of 116 (B) original items were longer, so about 20% of their text was unseen. Hidden text can hide a
  success, and can also hide context that changes how a visible one should be read. It was more common
  for aligned-redteam (98% of items, against 77% for abliterated-plain on A). The direction of its
  effect on contrasts is not established.
- **Ties count as failures.** Unresolved disagreements are labelled false in every arm. If ambiguity
  differs by arm, this can bias a contrast either way.
- **Pooled miss rate** for the original arms (pre-registered). Its effect is shown in the sensitivity
  analyses.

## Scope and limitations

- **Labels:** AI annotators only (two instances of one model), with no human validation sample. This is
  the main open weakness.
- **Attackers:** every attacker is from the Qwen family, including Jailbreak-R1, so none is independent
  of that lineage.
- **Abliteration:** one community abliteration (huihui-ai v2; its model card describes
  implementation-specific changes).
- **Prompts:** one red-team system prompt and one plain instruction.
- **Targets:** two small 2024-era models; nothing here speaks to frontier or closed models.
- **Scale:** 150 goals (146 in E1), StrongREJECT only, one stochastic collection per cell, 3 attempts
  per goal. Bootstrap intervals cover goal sampling, not run-to-run variation.
- **Harness:** a simplified, judge-free refinement loop in the spirit of PAIR, not a canonical PAIR or
  TAP implementation, so no claim of competitive attack strength is made.

## Reproducing

The data (scored transcripts, labelling keys, labels) is gitignored because it contains model-generated
harmful text, so the final numbers cannot be reproduced from the repository alone. With the local
`adj/` folder and `*_scored.json` files:

```bash
python redteam.py --selftest          # attack loop, template attacker, refusal checks, metrics
python estimate.py --selftest         # estimator validation incl. correlated-outcome coverage
python reproduce_results.py           # every number in this file -> results_numbers.json
python summarize.py A=A_scored.json B=B_scored.json --thr 0.7     # attacker behaviour, judge agreement
python estimate.py --scored A_scored.json --key adj/A_key.json --labels adj/A_labels_final.json --legacy-estimator   # pre-registered estimator
```

To re-collect and re-label from scratch:

- **Models, revisions and settings** are listed in `MANIFEST.md`.
- **StrongREJECT judge:** `sr_judge.py` reads `judge_templates.json`, which is included, with its source
  and hash in `MANIFEST.md`.
- **Historical labelling sheets** were cut at 1,600 characters, so regenerate them with
  `estimate.py --sample ... --max-chars 1600`.

## History

Superseded results, deviations and corrections are logged in `ANALYSIS-PLAN.md`, rather than rewritten:

- **D1–D4:** labelling events;
- **C1:** earlier "hand validation" claims rested on the assistant's own labels;
- **C2:** refusal figures and a rounding fix;
- **C3:** this revision — estimator replaced, verdicts revised, claims narrowed.

Earlier versions of this file are in git history. The judge-only ("screen-level") results that preceded
labelling are in commit `407c47c` and earlier.
