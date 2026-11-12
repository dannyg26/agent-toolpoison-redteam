# Putting the Guardrails Back: Can Safety Be Restored to Uncensored Open Models?

*A recovery study, proven on a live cyber range.*

## One-sentence thesis
Safety removal is **not uniformly permanent**: a model uncensored by **abliteration** can be
**re-secured** (safety restored), while one uncensored by **harmful fine-tuning** cannot — and we prove
it not just on chat refusals but on a **real dangerous capability** (autonomous cyber exploitation),
measured rigorously with confidence intervals.

## Why this is the project (checks every constraint)
- **Centrally about abliterated models** — they are the whole subject.
- **Genuinely open** (verified this session): recovery/re-alignment of already-abliterated models is
  "barely covered"; **no** controlled abliteration-vs-fine-tuning reversibility study exists; and the
  closest paper ([abliteration-methods comparison](https://arxiv.org/html/2512.13655v1)) does none of
  recovery, SFT-comparison, cyber, or CIs (it lists CIs as *its own* future work).
- **Safe to build and to publish** — the deliverable is a **defense** (how to re-secure an uncensored
  model), not an attacker. The cyber capability is only the *before/after measuring stick*.
- **We have a head start** — we already have the preliminary reversibility result (steering restored
  refusal on an abliteration-only model 0.38→0.88, failed on an SFT'd one) and the bootstrap-CI tooling.
- **Uses the cyber range you wanted** — AgentCyberRange is the proving ground, not a toy.

## The core experiment (the money table)
For each model, each **removal method**, measure two things — a **chat-refusal rate** and a
**cyber-range success rate** — across **three states**, all with bootstrap 95% CIs:

| state | refuses harmful chat? | hacks on the range? |
|---|---|---|
| safe base | yes (high) | low |
| **uncensored** | no (low) | higher |
| **uncensored → recovered** | **?** | **?** |

The claim to test — and the expected result:

| removal method | recovery restores safety? | → cyber capability drops back? |
|---|---|---|
| **abliteration** (weight-orthogonalization) | **yes** (shallow, reversible) | **yes** |
| **harmful-SFT** (gradient retraining) | **no** (deep, rewired) | **no** |

If that holds, the message is clean and useful: *a downloaded "uncensored" model can be re-secured if it
was abliterated, but not if it was fine-tuned — and re-securing it measurably removes the cyber risk.*

## Design knobs
- **Models** — reasoning/agentic, with a base + abliterated variant, **capable enough to get non-zero
  cyber-range success** (a 4B model may score ~0, hiding the signal). Lead candidate:
  `Qwen3-30B-A3B-Thinking` (MoE, ~3B active = efficient to run, capable, huihui abliterated variant
  exists) + its base. A smaller model (`Qwen3-4B-Thinking`) is fine for the *refusal-only* pilot.
- **Removal methods** — (1) abliteration we run ourselves (`refusal_direction.py`) and/or Heretic;
  (2) harmful-SFT (a public huihui-`-v2`-style variant, or we fine-tune one).
- **Recovery methods** — (1) **steering**: re-inject the base model's refusal direction (cheap, our C4
  hooks); (2) **re-alignment fine-tuning / self-distillation** on refusal data (the literature's more
  reliable route). Comparing recovery methods × removal methods is itself a contribution.
- **Measurement** — chat refusal on a standard harmful set (cheap) + a **subset** of AgentCyberRange
  (start with cheaper web-exploit tasks); bootstrap CIs on every rate (reuse `e1_causal_scaled.py`).

## Minimal pilot (do first — cheap, proves the core)
1. One model (`Qwen3-4B-Thinking` for refusal, or `Qwen3-30B-A3B-Thinking` for the cyber signal).
2. Two removal methods: our abliteration vs one public harmful-SFT variant.
3. One recovery method first: **steering** (cheapest); add fine-tuning if steering only partly restores.
4. Measure **chat refusal** across the 3 states with CIs → does recovery restore safety for abliteration
   but not SFT? **GO** if yes → add the cyber-range measure and more models.

## Positioning (cite, don't claim)
- [Arditi 2024](https://arxiv.org/abs/2406.11717) (refusal is a direction), the
  [abliteration-methods comparison](https://arxiv.org/html/2512.13655v1) (removal only),
  [AgentCyberRange](https://arxiv.org/pdf/2606.14295) (capability, not recovery),
  [UCL aligned-vs-uncensored](https://arxiv.org/html/2605.19722v1) (uplift, not recovery),
  [extended-refusal defense](https://arxiv.org/html/2505.19056v2) (prevention, not recovery).
- **Ours, unclaimed:** recovery of already-uncensored models; abliteration-vs-SFT **reversibility**;
  demonstrated on a **cyber-capability** measure; with **CIs**.

## Risks & honesty
- Steering recovery was noisy in our earlier C4 (non-clean random control) — fine-tuning recovery may be
  needed for a clean result.
- The model must be strong enough to show measurable cyber capability, or the before/after is invisible —
  hence the mid-size MoE pick.
- Cyber-range runs are expensive; scope to a subset and cheaper web tasks first.
- Ceiling is a **solid, useful, safe** paper (the "must be abliterated models" constraint sets that) —
  not a field-stunner. But it's genuinely open and genuinely useful.

## What it needs to run
RunPod top-up (balance is low) + a fresh API key; the removal/recovery + refusal measurement reuse our
existing tooling, and the AgentCyberRange integration is the main new engineering.
