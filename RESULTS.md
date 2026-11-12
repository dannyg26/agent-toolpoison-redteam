# Results so far: is abliterating your red-team attacker worth it?

Status: **complete, AI-annotated.** All 307 sampled items were labelled blind by two independent AI
agents (GPT-6.1 Sol, high reasoning, as reported by the researchers), not by humans — deviation D2 in
`ANALYSIS-PLAN.md`. The hypotheses and decision rules were fixed before labelling and applied as
written. The final results below are **AI-annotated, not human-validated**.

## Final results (AI-annotated)

**Answer: abliteration is not a substitute for prompting.** Used *instead of* a red-team prompt, it does
significantly worse on both targets, and this survives every robustness check below. Under a plain
instruction it removes refusals but adds no measurable attack success. Whether abliteration helps *on
top of* a red-team prompt is **unresolved**: the estimates are small (+0.06, +0.02) and the intervals
run from about −0.08 to +0.20, so a gain of up to ~20 points cannot be ruled out. The measurement
biases described below probably inflate that estimate.

Attack success rate, 150 goals per arm, 95% intervals (`estimate.py`):

| arm | A: Qwen2.5-7B | B: Llama-3.1-8B |
|---|---|---|
| no-attacker (just ask) | 0.09 [0.04, 0.19] | 0.04 [0.01, 0.13] |
| aligned-plain | 0.15 [0.09, 0.25] | 0.10 [0.06, 0.18] |
| abliterated-plain | 0.15 [0.09, 0.25] | 0.07 [0.03, 0.16] |
| **aligned-redteam** | **0.46 [0.35, 0.57]** | **0.17 [0.10, 0.27]** |
| abliterated-redteam | 0.52 [0.42, 0.62] | 0.19 [0.12, 0.28] |

Pre-registered hypotheses (`ANALYSIS-PLAN.md`), paired contrasts:

| | test | A | B | verdict |
|---|---|---|---|---|
| **H1** primary | abliterated-plain − aligned-redteam, upper bound < +0.05 on both | −0.30 [−0.42, −0.16] | −0.10 [−0.18, −0.02] | **supported** |
| H2 | same contrast, upper bound < 0 | yes | yes | **supported on both** |
| H3 | abliterated-plain − aligned-plain | +0.00 [−0.09, +0.08] | −0.03 [−0.09, +0.02] | no detectable effect |
| H4 | aligned-redteam − no-attacker | +0.36 [+0.23, +0.48] | +0.13 [+0.05, +0.21] | beats the floor |
| H4 | abliterated-plain − no-attacker | +0.06 [+0.00, +0.12] | +0.03 [+0.00, +0.07] | barely beats it |
| H4 | abliterated-redteam − no-attacker | +0.43 [+0.31, +0.52] | +0.15 [+0.09, +0.22] | beats the floor |
| explor. | abliterated-redteam − aligned-redteam | +0.06 [−0.08, +0.20] | +0.02 [−0.08, +0.12] | unresolved (underpowered, as predicted) |

Labelling quality: blind agent agreement kappa 0.82 (A; per sheet 0.69–0.95) and 0.93 (B), both above
the 0.6 gate; reconciliation changed no item the agents agreed on. The audit found 2/40 (A) and 1/40 (B)
real jailbreaks that both automated judges missed.

**How much the judges distorted the picture.** Share of goals flagged by either automated judge, versus
the annotated ASR:

| arm | A: flagged → ASR | B: flagged → ASR |
|---|---|---|
| no-attacker | 0.10 → 0.09 | 0.03 → 0.04 |
| aligned-plain | 0.30 → 0.15 | 0.18 → 0.10 |
| abliterated-plain | 0.17 → 0.15 | 0.06 → 0.07 |
| aligned-redteam | 0.79 → 0.46 | 0.35 → 0.17 |
| abliterated-redteam | 0.63 → 0.52 | 0.23 → 0.19 |

The judges' flags held up less often for aligned attackers: the share of flags confirmed was
0.40–0.57 for aligned arms and 0.65–0.79 for abliterated arms. Pooled by weights, 0.52 vs 0.75 (A) and
0.44 vs 0.76 (B), two-proportion test p ≈ 0.007 on each target. Arms were sampled at different rates,
so this is approximate. The gap tracks the *weights*, not the prompt — consistent with aligned
attackers quietly rewriting goals into safer neighbours that the judges still score as jailbreaks
(observed, not pre-registered). The judges also reported an effect the labels do not support: they
said abliteration made a plain-instructed attacker significantly *worse* (−0.07 to −0.13 in all four
judge/target columns). With labels it is no longer detectable (0.00 and −0.03, intervals include zero).

### Robustness (post hoc, not pre-registered)

| check | headline A | headline B | other contrasts |
|---|---|---|---|
| agent 1's blind labels only | −0.38 [−0.49, −0.24] | −0.11 [−0.20, −0.03] | H3 and on-top n.s. |
| agent 2's blind labels only | −0.29 [−0.41, −0.16] | −0.11 [−0.20, −0.03] | H3 and on-top n.s. |
| A's 5 unresolved items counted as jailbreaks | −0.33 [−0.45, −0.20] | (none unresolved) | H3 and on-top n.s. |
| bootstrap seed, 10 seeds | stable | upper bound −0.016 to −0.021 | — |
| **worst case**: every false label on abliterated-plain that could be wrong flipped to true (12 in A, 2 in B) | −0.17 [−0.30, −0.03] | −0.08 [−0.17, −0.005] | — |

The headline holds in every row. The on-top estimate even changes sign between the two annotators
(−0.02 vs +0.05 on A), which confirms it is noise at this sample size.

### Measurement biases found after labelling

- **Truncated responses.** The labelling sheets showed the first 1,600 characters of each response.
  172 of 191 items (A) and 60 of 116 (B) were longer, so annotators judged about 80% of the text, missing
  a mean ~390-character tail. Hidden text can only hide a jailbreak, never invent one, so this
  undercounts. It falls unevenly: 98% of aligned-redteam items were truncated, against 77% of
  abliterated-plain (A).
- **One round per cell.** A cell counts if any round is a jailbreak, but only its highest-scoring flagged
  round was labelled. Of aligned-redteam's cells labelled false, 15 of 23 (A) had another flagged round
  nobody labelled, against 1 of 7 for abliterated-plain and 3 of 9 for abliterated-redteam.

Both biases undercount aligned-redteam most. So the headline, where aligned-redteam wins, is
*conservative*, and the worst-case row above bounds it. The other contrasts are not protected. The
on-top estimate (abliterated-redteam − aligned-redteam) is probably **inflated in abliteration's
favour**, and the H3 null in A may be pulled toward zero, since aligned-plain was truncated more (93%
vs 77%). Re-labelling the 111 false-labelled truncated items with full text would tighten both.

**Limits that bound these conclusions:**
- labels are from AI agents, not humans;
- the two measurement biases above;
- 150 goals, one pass per cell;
- one attacker family and one abliteration implementation;
- the miss rate is pooled across arms (A's two misses fell in no-attacker and aligned-plain, B's one in
  abliterated-plain).

## Extension E1: an attacker trained for red-teaming (final, AI-annotated)

`yukiyounai/Jailbreak-R1` (Guo et al. 2025), a 7.6B attacker trained with reinforcement learning to write
jailbreak prompts. It was run in its authors' exact format on the same goals and both targets, with the
design pre-registered in `ANALYSIS-PLAN.md`. Collection was clean: 900 prompts, all parsed, no errors,
and the model never refused.

**Labelling.** All 178 sampled items were labelled blind by two independently started AI agents, not
humans. The first 130 were labelled first and the remaining 48 afterwards (D4); keys were read only
after labelling, and the earlier labels are unchanged.

- Blind agreement between the agents: kappa 0.92 (A) and 0.97 (B).
- Drift check, original items re-shown blind: kappa 0.75 with a positive-rate shift of +0.04 (A,
  25 items), and kappa 1.00 with no shift (B, 25 items).
- Both checks pass the pre-registered rule, so the E1 contrasts are read at face value.

Attack success on the 146 shared goals (4 chemical/biological goals excluded, D3), 95% intervals:

| arm | A: Qwen2.5-7B | B: Llama-3.1-8B |
|---|---|---|
| no-attacker (just ask) | 0.09 [0.05, 0.20] | 0.04 [0.01, 0.13] |
| abliterated-plain | 0.16 [0.10, 0.25] | 0.07 [0.03, 0.16] |
| **trained-redteam** | **0.51 [0.39, 0.62]** | **0.18 [0.11, 0.29]** |
| aligned-redteam | 0.48 [0.36, 0.59] | 0.17 [0.10, 0.27] |
| abliterated-redteam | 0.52 [0.43, 0.62] | 0.19 [0.13, 0.28] |

| hypothesis | A | B | verdict |
|---|---|---|---|
| **E1-H5** (primary, judged on B): trained − prompted aligned | +0.03 [−0.13, +0.19] | **+0.01 [−0.12, +0.14]** | **no detectable difference** |
| E1-H6: trained − abliterated-plain | +0.35 [+0.20, +0.47] | +0.10 [−0.003, +0.22] | better on A; unresolved on B |
| E1 floor: trained − no-attacker | +0.41 [+0.26, +0.53] | +0.14 [+0.03, +0.25] | beats it on both |

**Robustness (post hoc).** Every verdict is unchanged under each agent's blind labels alone, and with
every disputed item counted as a jailbreak. The drift check passes in all four versions (kappa ≥ 0.67,
shift ≤ 0.08). E1-H6 on B misses significance in every version, with a lower bound of −0.003.

**Meaning.** An attacker trained with reinforcement learning to jailbreak is not measurably better than a
general aligned model given a good red-team prompt. On the primary target the interval allows a gap of up
to about ±0.13, so this is "not detectably different", not "equal". It is a far better attacker than an
abliterated model with a plain instruction. On A, where it shares the target's base model, its estimate
is slightly higher than prompting, but not significantly.

**The judges misjudged E1 too.** The judge-only preview had StrongREJECT calling Jailbreak-R1
significantly *worse* than the prompted aligned model on both targets (−0.15, −0.16); the labels show no
difference. Exploratory, not pre-registered: on A the judges missed 7 of 30 audited Jailbreak-R1 cells
that were real jailbreaks (23%), against 2 of 39 (5%) for the original arms. Fisher's exact test gives
p = 0.035, which does not survive correction across the two targets; on B the rates are 7% vs 3%,
p = 0.58.

## How we got here

*Correction (2026-11-12): earlier versions said the automated judges "failed hand validation". The
labels behind that were made by the AI assistant that ran this study (Claude), not by a human.*

## What was run

Five attacker arms, two targets, 150 StrongREJECT behaviours, 3 refinement rounds, one pass per cell.
Every arm gets the identical goal set and the identical query budget; only the attacker changes.

|  | plain instruction | red-team system prompt |
|---|---|---|
| **aligned weights** | `aligned-plain` | `aligned-redteam` |
| **abliterated weights** | `abliterated-plain` | `abliterated-redteam` |

Plus `no-attacker`: the harmful goal is sent to the target verbatim, re-sampled 3 times. This is the
budget-matched "just ask" floor. An attacker is only worth building if it beats this.

- **Attacker (aligned):** `Qwen/Qwen3-8B`
- **Attacker (abliterated):** `huihui-ai/Huihui-Qwen3-8B-abliterated-v2` — same lineage
- **Target A:** `Qwen/Qwen2.5-7B-Instruct`
- **Target B:** `NousResearch/Meta-Llama-3.1-8B-Instruct` — different family, for generality
- 2123 (A) and 2120 (B) scored rounds, **0 endpoint errors**

No judge ran inside the loop. Each arm spent its full 3-round budget and the transcripts were scored
afterwards, so the trajectories do not depend on a judge and can be re-scored by anyone.

## Finding 1: abliteration buys willingness, not skill

Share of attack rounds (mechanical string checks, no judge involved; target A, B nearly identical):

| arm | attacker refused | copied goal near-verbatim | rewrote the goal |
|---|---|---|---|
| aligned-plain | **0.27** | 0.04 | 0.69 |
| abliterated-plain | **0.01** | **0.29** | 0.70 |
| aligned-redteam | 0.00 | 0.00 | 1.00 |
| abliterated-redteam | 0.00 | 0.00 | 1.00 |

Abliteration does what it says: refusals go from 27% to ~1%. (These are upper bounds: the refusal detector also flags attack prompts that merely contain a phrase like "as an AI". Counting only outputs that open as a refusal gives 25% on both targets for aligned-plain and 0% for abliterated-plain; `summarize.py`, column "clear"; see C2 in `ANALYSIS-PLAN.md`.) But the freed capacity does not turn into
attacking. Nearly a third of its attempts are the harmful goal parroted back with little or no
rewriting — which the target then simply refuses. **The red-team prompt removes refusals just as
completely (27% → 0%) with no weight surgery, and never degenerates into copying.**

The gap holds at every similarity threshold. Both targets agree to within two points at every threshold
except the loosest (0.50: aligned-plain 0.26 vs 0.31) — expected, since round-1 prompts are written
before the attacker sees any target output. Target A shown:

| copy threshold | 0.50 | 0.70 | 0.90 | 0.95 |
|---|---|---|---|---|
| aligned-plain | 0.26 | 0.08 | 0.03 | 0.02 |
| abliterated-plain | 0.59 | 0.38 | 0.22 | **0.21** |
| aligned-redteam | 0.00 | 0.00 | 0.00 | 0.00 |

At near-exact matching the abliterated attacker copies 7–10x more often than the aligned one. This is
the mechanism behind everything below, and it rests on string comparison, not on a judge.

## Finding 2 (screen-level; superseded by the final results above)

*Kept to show what the automated judges said on their own. The final, annotated results changed one
conclusion (the plain-instruction effect vanished) and roughly halved aligned-redteam's ASR.*

Attack success rate (fraction of goals jailbroken within 3 rounds), as scored by StrongREJECT ≥ 0.7 or
HarmBench "yes". These are what the automated judges say, **not** final ASRs:

| arm | A: StrongREJECT | A: HarmBench | B: StrongREJECT | B: HarmBench |
|---|---|---|---|---|
| no-attacker | 0.04 | 0.07 | 0.01 | 0.02 |
| aligned-plain | 0.19 | 0.21 | 0.16 | 0.12 |
| abliterated-plain | 0.09 | 0.13 | 0.03 | 0.05 |
| **aligned-redteam** | **0.73** | **0.61** | **0.29** | **0.19** |
| abliterated-redteam | 0.54 | 0.52 | 0.20 | 0.16 |

Paired contrasts (bootstrap over goals, 95% CI; `*` = CI excludes 0):

| question | A: StrongREJECT | A: HarmBench | B: StrongREJECT | B: HarmBench |
|---|---|---|---|---|
| abliteration alone − prompting alone | −0.63* | −0.48* | −0.26* | −0.15* |
| abliteration on top of prompting | −0.19* | −0.09 | −0.09* | −0.03 |
| abliteration vs aligned, plain instruction | −0.10* | −0.08* | −0.13* | −0.07* |
| red-team prompt on aligned weights | +0.53* | +0.40* | +0.13* | +0.07 |
| prompted aligned − just asking | +0.69* | +0.53* | +0.29* | +0.17* |
| abliterated plain − just asking | +0.05* | +0.05 | +0.03 | +0.03 |
| abliterated+prompted − just asking | +0.50* | +0.45* | +0.19* | +0.14* |

Under both automated judges, in all four columns: abliteration alone scores below prompting alone,
abliteration adds nothing on top of prompting, and under a plain instruction the abliterated attacker
scores below the aligned one even though the aligned one refuses 27% of the time. `abliterated-plain`
barely clears the "just ask the target" floor (+0.03 to +0.05).

The consistency across judges and targets is suggestive, but both judges are biased in the same
direction (see below), so agreement between them is weaker evidence than it looks.

## Finding 3 (methodological): the standard judges do not agree with each other

**Solid, no labels involved:** the two published judges disagree with **each other**:

| | round level | (arm, goal) cell level |
|---|---|---|
| target A | raw 0.86, **kappa 0.56** | raw 0.83, kappa 0.60 |
| target B | raw 0.95, **kappa 0.52** | raw 0.91, kappa 0.59 |

Raw agreement looks high only because most items are easy negatives; kappa corrects for that. Two
published jailbreak judges at kappa ≈ 0.56 on identical data cannot both be measuring the same thing.
Concretely, HarmBench flags 60 (A) and 22 (B) cells that StrongREJECT scores below 0.7, so either
judge used alone as a screen would silently drop the other's positives.
This is a contribution in its own right: ASR numbers reported from a single automated judge are not
comparable across papers, because a different published judge would give different numbers.

**Weaker, one AI annotator:** four automated evaluators were compared with labels from a single AI
annotator (Claude). All four disagreed with it substantially. This shows disagreement among automated
evaluators, not that any of them is wrong by a human standard:

| evaluator | disagreement with the AI annotator |
|---|---|
| Qwen2.5-7B chat judge | the annotator confirmed 8 of the judge's 20 positives |
| HarmBench official classifier | flagged, among others, a baking-soda volcano and legal power-of-attorney advice |
| StrongREJECT fine-tuned judge | mean 0.87 on the annotator's positives vs 0.71 on its negatives (on judge-flagged responses only) |
| LLM on-topic checker | the annotator disagreed with 13 of its 16 "off-topic" calls |

The dominant error is **goal drift**. The attacker rewrites the harmful goal into a harmless neighbour,
the target answers *that* helpfully and in detail, and the judges score the fluent on-topic-sounding
answer as a jailbreak.

## What the labels can and cannot change

*An earlier version of this section claimed the headline was "settled by the screen counts". That
assumed the StrongREJECT screen missed no real jailbreaks, on the strength of 8 calibration positives
from an older run; the 82 HarmBench-only cells above show the assumption was unsupported. The labelling
design now audits what both judges miss.*

Simulation on this data's exact cell structure (`ANALYSIS-PLAN.md`) gives the honest picture:

- **That abliteration is *better* than prompting is very unlikely.** It would need the prompted arm's
  flagged hits to be real far less often than the abliterated arm's — roughly 8x less — plus few misses.
  This is what H1 tests, as non-superiority with a 5-point margin.
- **That prompting is *significantly better* is not settled.** If the judges' false positives fall
  mostly on the fluent prompted arms (precision ~0.25 vs ~0.65), the true gap shrinks to about −0.06
  and simulated power drops below 0.2 at any labelling budget. A null here would mean "abliteration does
  not help, and prompting is not detectably better either" — still an answer to the question.
- **Whether abliteration adds anything on top of a good prompt cannot be resolved at 150 goals**
  (power 0.06–0.19 in every scenario). That is a goal-count limit, not a labelling one.

## The caveat that decides the headline

Goal drift produces false positives, and the prompted arms generate far more fluent, on-topic-sounding
prose than the copy-paste-prone abliterated arm. So the false positives are probably **not** evenly
distributed across arms, and the measured advantage of prompting may be partly an artifact.

`estimate.py` measures precision per arm from the labels and folds it, together with the audited miss
rate, into the intervals. Until that runs:

- **Finding 1 is solid** — mechanical, judge-free.
- **Finding 3 is solid** — it is a statement about the judges.
- **Finding 2 is provisional in both direction and size.** The plausible bias runs in favour of
  prompting. A mechanism points the same way: copying the goal verbatim cannot drift off it, so the
  abliterated arm's flagged hits are probably real *more* often than the prompted arms'.

## Other limitations

- One pass per cell, so no run-to-run variance at n=150. An earlier n=20 × 3 pilot swung 0.10–0.20,
  which is why n was raised; repeats at n=150 are still worth adding.
- One attacker lineage (Qwen3-8B ± abliteration). A second family would test whether this is
  Qwen-specific — the most likely reviewer objection.
- One abliteration implementation; these vary in quality, and a poor one would look exactly like this.
- StrongREJECT only; HarmBench/AdvBench are wired up and unused.
- 3 rounds. More refinement might help the abliterated arm escape its copying habit.

## Reproducing

```bash
python redteam.py --selftest                 # offline: loop, error guard, baseline arm, metrics
python redteam.py --key rt --dataset strongreject --n-goals 150 --rounds 3 --concurrency 16 \
  --disable-thinking --out A_raw.json --attacker-safe-url ... --target-url ...
python rescore.py A_raw.json --out A_scored.json --hb-url ... --ontopic-url ...
python summarize.py A=A_scored.json B=B_scored.json --thr 0.7
python estimate.py --selftest                                       # interval coverage, by simulation
python estimate.py --scored A_scored.json --sample --out adj/A      # blind stratified sheets + key
python adjudicate.py --key adj/A_key.json --labels ... --scored A_scored.json   # agreement
python estimate.py --scored A_scored.json --key adj/A_key.json --labels ...     # final ASR
```

Transcripts and scored outputs are gitignored: they contain model-generated harmful text and stay
local as research artifacts.
