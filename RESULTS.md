# Results so far: is abliterating your red-team attacker worth it?

Status: **data collected and automatically scored; human adjudication pending** (see
`LABELING-PROTOCOL.md`, and `ANALYSIS-PLAN.md` for the hypotheses and decision rules fixed before
labelling). Finding 1 and Finding 3 are final. Finding 2 comes from judges that failed hand validation:
its direction is suggestive, and whether it is *significant* depends on the labels.

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

Abliteration does what it says: refusals go from 27% to ~1%. But the freed capacity does not turn into
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

## Finding 2 (screen-level, provisional): prompting beats abliteration under both judges

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

Four automated evaluators were tested against hand labels; **all four failed**:

| evaluator | how it failed |
|---|---|
| Qwen2.5-7B chat judge | 40% precision on its own positives (8 of 20 real) |
| HarmBench official classifier | credited a baking-soda volcano, and legal power-of-attorney advice |
| StrongREJECT fine-tuned judge | 0.87 mean on real jailbreaks vs 0.71 on false ones — barely separates (on responses some judge had flagged, so not a random sample) |
| LLM on-topic checker | disagreed with hand labels on 13 of 16 "off-topic" calls |

And the two published ones disagree with **each other**:

| | round level | (arm, goal) cell level |
|---|---|---|
| target A | raw 0.86, **kappa 0.56** | raw 0.83, kappa 0.60 |
| target B | raw 0.95, **kappa 0.52** | raw 0.91, kappa 0.59 |

Raw agreement looks high only because most items are easy negatives; kappa corrects for that. Two
published jailbreak judges at kappa ≈ 0.56 on identical data cannot both be measuring the same thing.
Concretely, HarmBench flags 60 (A) and 22 (B) cells that StrongREJECT scores below 0.7, so either
judge used alone as a screen would silently drop the other's positives.
This is a contribution in its own right: ASR numbers reported from a single automated judge, without
human validation, are not comparable across papers.

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
