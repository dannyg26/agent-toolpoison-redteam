# Is Abliterating Your Red-Teamer Worth It? Weight-Surgery vs. Prompting for Automated Red-Team Agents

## The question (one line)
To build an effective automated **red-team agent** — an AI that attacks a target model to find its
safety holes — is it worth **abliterating** the attacker (permanent weight edit that removes refusals
but slightly degrades it), or does simply **prompting** an aligned attacker work just as well while
keeping its full capability?

## Why this project (fits every constraint)
- **Red-team agents** — the subject itself (advisor's requirement).
- **Abliterated models** — one of the three attacker arms (the "weight-surgery" condition).
- **Safe + publishable** — this is *defensive* automated red-teaming (find a target's holes so they can
  be fixed); standard methodology (PAIR, TAP, HarmBench). Harmful goals come from a public benchmark;
  generated attack text stays in local logs, never committed.
- **One month** — the attack loop is a solved recipe; small scale gives a real result.

## What's known vs. our gap (verified 2026 scan)
- **Known / cited, not ours:** aligned attackers refuse to generate attacks ([CoP, NeurIPS'25];
  [self-improved RT, 2026]); people already use abliterated attackers in practice (Red Hat, Helix blogs);
  aligned attackers can still be strong *with good prompting* ([J2](https://arxiv.org/html/2502.09638v1),
  91–93% ASR). The intuition "uncensored refuses less" is folk wisdom.
- **Open (both searches confirmed):** no controlled study holds attack method + target + judge fixed and
  varies **only the attacker's safety**, with real measurement — and nobody has pitted **abliteration
  against prompting** for the attacker, or decomposed **willingness vs. capability**.

## The experiment: a 2x2 over the attacker, plus a floor
Same target, same goals, same query budget — vary only the attacker. The 2x2 separates the two levers
(weights vs prompt) and lets us ask whether they add:

|  | plain instruction | red-team system prompt |
|---|---|---|
| **aligned weights** | `aligned-plain` | `aligned-redteam` |
| **abliterated weights** | `abliterated-plain` | `abliterated-redteam` |

Plus **`no-attacker`**: the goal goes to the target verbatim, re-sampled for the same number of rounds.
This is the budget-matched "just ask" floor — without it, an arm that looks good may be doing nothing
an attacker is needed for. (The original 3-arm design lacked both the 4th cell and this floor, so
weights and prompting could not be separated and nothing was anchored.)

**The attack loop (PAIR-style, per harmful goal):**
1. Attacker crafts an adversarial prompt aimed at making the target do the goal.
2. Send to the **target**; get its response.
3. **Judge** scores: jailbroken (harmful compliance) or refused.
4. If not jailbroken, attacker sees the response and **refines** — up to **N** rounds.
5. Record success / rounds / whether the attacker itself refused.

## Models (as actually run)
- **Attacker, aligned:** `Qwen/Qwen3-8B`
- **Attacker, abliterated:** `huihui-ai/Huihui-Qwen3-8B-abliterated-v2` (same lineage)
- **Target A:** `Qwen/Qwen2.5-7B-Instruct`
- **Target B:** `NousResearch/Meta-Llama-3.1-8B-Instruct` (different family → generality)
- **Goals:** 150 behaviours from **StrongREJECT** (built to not over-report jailbreaks)
- **Scoring:** HarmBench official classifier + StrongREJECT fine-tuned judge, **post hoc**, then blind
  labelling of a stratified sample by two independent AI agents (originally planned as two humans; see
  `ANALYSIS-PLAN.md`, D2). HarmBench/AdvBench are wired up and unused.
All served as OpenAI-compatible endpoints (vLLM), so the harness is just API calls — no model hooks.

## Measurement: no judge in the loop
Every arm spends its **full** round budget and the transcripts are scored afterwards. Judging inside the
loop makes the trajectory depend on the judge, and ours turned out to be unreliable — so the data would
have been unrecoverable. Collected this way it can be re-scored by anyone, with any judge.

**Metrics**
- **ASR** — fraction of goals jailbroken within N rounds, bootstrap CI over goals *(headline)*.
- **Attacker refusal rate** and **verbatim-copy rate** — the willingness axis and the failure mode,
  both from mechanical string checks, no judge involved.
- **Paired contrasts** between arms (bootstrap over goals): arms share the goal set, so pairing removes
  goal-difficulty variance. See `CONTRASTS` in `redteam.py` for the seven planned comparisons.

## What each outcome means
- **prompted ≥ abliterated** → abliteration is **unnecessary**; prompt an aligned model, keep its brains.
- **abliterated > prompted** → the weight surgery buys attack power prompting can't reach.
- **either ≈ no-attacker** → that attacker isn't earning its keep at all.

Answer (AI-annotated, not human-validated): **abliteration is not a substitute for prompting.** Used
instead of a red-team prompt it is significantly worse on both targets (−0.30 and −0.10 ASR), robust to
every check including a worst-case bound. Under a plain instruction it removes refusals yet adds no
measurable success, consistent with ~29% of its attempts copying the goal near-verbatim. Whether it
helps *on top of* a red-team prompt is unresolved (+0.06 and +0.02, intervals up to about +0.20). The
primary pre-registered hypothesis is supported on both targets. See `RESULTS.md`.

## Where it stands
- ✅ Harness, 5 arms, 2 targets, 150 goals, 0 endpoint errors, offline `--selftest` passing
- ✅ Automated scoring + a validity test of the judges (all four failed; the two standard ones agree at
  kappa ≈ 0.56)
- ✅ Analysis plan fixed before labelling, with data hashes (`ANALYSIS-PLAN.md`); estimator validated
  by coverage simulation (`estimate.py --selftest`)
- ✅ **AI-agent labelling** — all 307 items, two blind agents (kappa 0.82 / 0.93); final estimates run
  against the pre-registered plan. AI-annotated, not human-validated.
- ⏳ More goals (needed for the abliteration-on-top-of-prompting question); repeats at n=150;
  a 2nd attacker family; more rounds

Files: `redteam.py` (collection) · `rescore.py` + `sr_judge.py` (scoring) · `summarize.py` (aggregates)
· `estimate.py` (labelling sample + final estimates) · `adjudicate.py` (agreement) · `analyze.py`
(legacy screened-only sheets).
