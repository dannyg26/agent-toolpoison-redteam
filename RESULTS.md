# Results so far: is abliterating your red-team attacker worth it?

Status: **data collected and automatically scored; human adjudication pending** (see
`LABELING-PROTOCOL.md`). The numbers below come from judges that failed hand validation, so treat the
*direction* as the finding and the *magnitude* as provisional.

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

The gap holds at every similarity threshold, and both targets agree to within a point — expected, since
the attacker writes its first prompt before seeing any target output:

| copy threshold | 0.50 | 0.70 | 0.90 | 0.95 |
|---|---|---|---|---|
| aligned-plain | 0.26 | 0.08 | 0.03 | 0.02 |
| abliterated-plain | 0.59 | 0.38 | 0.22 | **0.21** |
| aligned-redteam | 0.00 | 0.00 | 0.00 | 0.00 |

At near-exact matching the abliterated attacker copies 7–10x more often than the aligned one. This is
the mechanism behind everything below, and it rests on string comparison, not on a judge.

## Finding 2: prompting beats abliteration, on both targets, under both judges

Attack success rate (fraction of goals jailbroken within 3 rounds):

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

Three things hold in all four columns:

1. **Abliteration alone loses to prompting alone**, decisively and significantly every time.
2. **Abliteration adds nothing on top of prompting** — negative in all four, significant in two.
3. **Abliteration is *worse* than leaving the attacker aligned** under a plain instruction, even though
   the aligned attacker refuses 27% of the time. Removing refusal made the attacker worse.

And `abliterated-plain` barely clears the "just ask the target directly" floor (+0.03 to +0.05, not
significant in three of four columns). An abliterated attacker given a plain instruction is close to
worthless as a red-team agent.

## Finding 3 (methodological): the standard judges do not agree with each other

Four automated evaluators were tested against hand labels; **all four failed**:

| evaluator | how it failed |
|---|---|
| Qwen2.5-7B chat judge | 40% precision on its own positives (8 of 20 real) |
| HarmBench official classifier | credited a baking-soda volcano, and legal power-of-attorney advice |
| StrongREJECT fine-tuned judge | 0.87 mean on real jailbreaks vs 0.71 on false ones — barely separates |
| LLM on-topic checker | disagreed with hand labels on 13 of 16 "off-topic" calls |

And the two published ones disagree with **each other**:

| | round level | (arm, goal) cell level |
|---|---|---|
| target A | raw 0.86, **kappa 0.56** | raw 0.83, kappa 0.60 |
| target B | raw 0.95, **kappa 0.52** | raw 0.91, kappa 0.59 |

Raw agreement looks high only because most items are easy negatives; kappa corrects for that. Two
published jailbreak judges at kappa ≈ 0.56 on identical data cannot both be measuring the same thing.
This is a contribution in its own right: ASR numbers reported from a single automated judge, without
human validation, are not comparable across papers.

The dominant error is **goal drift**. The attacker rewrites the harmful goal into a harmless neighbour,
the target answers *that* helpfully and in detail, and the judges score the fluent on-topic-sounding
answer as a jailbreak.

## The headline does not depend on the pending labels

Because the screen is high-recall, `ASR_arm = S_arm x precision_arm`, and `S_arm` is known exactly. So
each contrast has a **flip ratio**: how many times more precise one arm would have to be than the other
for the sign to reverse.

| contrast | A | B | |
|---|---|---|---|
| abliteration alone − prompting alone | 7.8x | 8.8x | **settled** |
| prompted aligned − just asking | 0.06x | 0.02x | settled |
| abliterated+prompted − just asking | 0.07x | 0.03x | settled |
| red-team prompt on aligned weights | 0.27x | 0.55x | settled in A |
| abliteration vs aligned, plain instruction | 2.1x | 4.8x | settled in B |
| abliteration on top of prompting | 1.35x | 1.47x | needs labels |

For the headline to reverse, the abliterated attacker's screened hits would have to be ~8x more often
real than the prompted attacker's. Given both were screened by the same judge on the same goals against
the same target, that is not a credible configuration. **The direction of the headline is settled by
the screen counts; adjudication sets its magnitude.**

The one genuinely open question is whether abliteration adds anything *on top of* a good prompt
(flip ratio ≈ 1.4). Both automated judges say no, but that one needs the labels.

## The caveat that decides the headline

Goal drift produces false positives, and the prompted arms generate far more fluent, on-topic-sounding
prose than the copy-paste-prone abliterated arm. So the false positives are probably **not** evenly
distributed across arms, and the measured advantage of prompting may be partly an artifact.

`adjudicate.py` reports screen precision per arm and flags exactly this, and `estimate.py` folds the
precision estimate into the CI. Until that runs:

- **Finding 1 is solid** — mechanical, judge-free.
- **Finding 3 is solid** — it is a statement about the judges.
- **Finding 2's direction is robust** (same sign in 4 independent columns), but its **magnitude is
  unverified**, and the plausible bias runs in favour of prompting.

The one contrast least exposed to this bias is *abliteration vs aligned under a plain instruction*
(−0.07 to −0.13, significant in all four columns): both arms share a prompt and a style, and the
mechanism is the measured 29% copy rate. That abliteration makes a plain-instructed attacker **worse**
looks safe to state now.

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
python analyze.py A_scored.json --thr 0.7 --sheet adj --tag A    # blind sheets for annotators
python adjudicate.py --key adj/A_key.json --labels ... --scored A_scored.json
```

Transcripts and scored outputs are gitignored: they contain model-generated harmful text and stay
local as research artifacts.
