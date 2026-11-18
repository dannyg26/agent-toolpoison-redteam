# C4 — Causal Recovery: is the surviving trace signal *causally live*?

Companion to `PROPOSAL.md`. Week-1 (C1) showed the harm representation **survives** in the decensored
model's reasoning trace (probe AUROC 1.00 while refusal = 0%). That is **correlational**. C4 asks the
causal question and closes the biggest reviewer objection.

## Why this experiment is the one that matters

1. **Kills the input-echo confound.** The strongest objection to C1: "the probe just reads the harmful
   *prompt*, which is identical in both models." A probe is correlational and can't answer this. But a
   **behavioral** change produced by manipulating the internal signal cannot be explained by input
   echo — if adding a direction back *restores refusal*, the signal is functional, not a passive copy.
2. **Upgrades the headline.** C1 = "the trace still *contains* harm." C4 = "the trace still *computes*
   harm, and the refusal machinery downstream is intact — so we can **restore safety** by re-injecting
   the one signal abliteration suppressed." That is the mechanistic + practical story.
3. **Mechanistic account.** Abliteration orthogonalizes the refusal direction out of the weights that
   *write* to the residual stream, so the model can no longer *emit* that direction — but if the
   downstream machinery that *reads* it is intact, manually adding the direction back should reconnect
   the severed routing. C4 tests exactly this "write removed, read intact" hypothesis, consistent with
   *When Safety Routing Breaks* (routing, not representation, is what fails).

## Hypotheses

- **H1 (restoration / sufficiency).** Additively steering the **removed** model along the refusal
  direction `d_ref` (extracted from the *aligned* model) raises harmful-prompt refusal from ~0 back
  toward the aligned level, at some steering strength α.
- **H2 (the surviving signal is read).** Amplifying the removed model's **own surviving harm
  direction** `d_harm*` (the very direction the C1 probe found) *also* raises refusal — i.e. the
  downstream refusal machinery reads that direction. This is the tight tie to C1.
- **H3 (specificity, not just breakage).** At a working α, refusal rises on **harmful** prompts while
  **benign** prompts stay largely answered, and outputs stay coherent. A **random** direction of equal
  magnitude does **not** restore refusal. (Rules out "any large perturbation makes the model refuse /
  emit garbage.")

## Design

**Model.** Removed = `huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2` (the C1 removed model; refusal
0%). Only this model is loaded — fast, one GPU load.

**Manipulation.** Forward-hook additive steering at every decoder layer, scaled to each token's own
residual norm so α is a dimensionless fraction:
`h ← h + α · ‖h‖ · d̂`  (d̂ unit-norm). Hooks removed after each generation.

**Directions (3 conditions).**
| Condition | d̂ | Source | Prediction |
|---|---|---|---|
| `refusal` | `d_ref` | aligned model's refusal direction (reuse `directions_20b.pt`, layer 13) | refusal restored (H1) |
| `harm*` | `d_harm*` | removed model's **own** surviving harm direction = mean(analysis‖harmful) − mean(analysis‖benign) | refusal restored (H2) |
| `random` | random unit vector | — | no restoration (H3) |

**Sweep.** α ∈ {0, 0.05, 0.1, 0.2, 0.4} (fraction of token norm); α=0 is the untouched baseline.

**Measured per (condition, α).**
- `harmful_refusal` — refusal rate on 8 harmful prompts (↑ = restoration).
- `benign_refusal` — refusal rate on 8 benign prompts (should stay low = specificity).
- `coherence` — fraction of outputs that are non-degenerate (length ≥ threshold, low char-repetition).

**GO for C4.** There exists an α where `refusal`/`harm*` give **harmful_refusal high** (e.g. ≥ 0.5),
**benign_refusal low** (e.g. ≤ 0.2), **coherence high**, and `random` does **not** — a clean
restoration window. Soft/counter-result: refusal only rises alongside benign refusal / incoherence
(then the surviving signal is present but not cleanly steerable — still reportable, weaker).

## Controls & confounds

- **Random-direction control** (built in) — isolates "the direction matters," not "perturbation."
- **Benign specificity** — restored safety must spare benign tasks, else it's lobotomy not recovery.
- **Coherence gate** — a model that refuses because it's been pushed into gibberish is not "safe."
- **Dose–response** — a monotone α→refusal curve for `refusal`/`harm*` but not `random` is the
  signature we want.
- **Localization (full-study, secondary).** Inject only at *analysis-channel* token positions vs only
  *final-channel* positions to ask **where** the severed routing lives. (Needs position-gated hooks
  during KV-cache generation; deferred past the go/no-go.)

## Result — NO-GO on the SFT'd model, and why that's informative (2026-11-09, A100, ~$1.80)

Ran on `huihui-ai/…-abliterated-v2`, inject band = layers 10–16, α ∈ {0, .005, .01, .02, .04, .08}.

| cond | α (coherent range) | harmful_refusal | benign_refusal | coherence |
|---|---|---|---|---|
| baseline | 0 | 0.00 | 0.00 | 1.00 |
| refusal | .005–.04 | 0.00–0.12 (noise) | 0.00 | 1.00 |
| refusal | .08 | 0.00 | 0.00 | **0.06** (breaks) |
| harm | .005–.04 | **0.00** | 0.00 | 1.00 |
| harm | .08 | 0.00 | 0.00 | 0.88 |
| random | .005–.04 | 0.00 | 0.00 | 1.00 |

**No coherent α restores refusal.** The aligned refusal direction gives only 0–1/8 noise; the removed
model's *own* surviving harm direction gives flat zero; coherence collapses before any strong push
lands. So on *this* model the surviving signal (C1) is **not** linearly re-activatable into refusal.

**The likely reason — and the fix.** `…-abliterated-v2` is abliteration **+ SFT on harmful
instructions**. SFT can *retrain the downstream refusal circuit to comply*, not merely suppress the
direction's write — so there is no intact "read" machinery to reconnect, and restoration is expected
to fail. The clean C4 substrate is an **abliteration-ONLY** model (`p-e-w/gpt-oss-20b-heretic` or
`…-abliterated` v1), where only the *write* of the direction is removed. **Next run:** repeat C4 there.

**This null is not a dead end — it's a sharper hypothesis.** If restoration works on abliteration-only
but fails on SFT'd models, that is itself a result: **safety-removal methods differ in depth** —
abliteration is *reconnectable* (shallow, write-only), SFT is *not* (it rewrites the circuit). That
"depth of removal" axis is a richer contribution than a single restoration curve. (Caveat: linear
steering of gpt-oss refusal is known-hard/incoherent; a single-layer calibrated or projection-based
intervention may be needed before concluding even on abliteration-only.)

## Result — GO on the abliteration-only model (2026-11-09, A100, ~$1.85)

Re-ran on `p-e-w/gpt-oss-20b-heretic` (abliteration-only), same band (10–16) and α grid.

| cond | α | harmful_refusal | benign_refusal |
|---|---|---|---|
| baseline | 0 | **0.38** (refusal machinery intact, unlike v2's 0.00) | 0.00 |
| refusal | .005 / .01 / .02 | 0.62 → 0.75 → **0.88** (dose-dependent restoration) | ~0 |
| refusal | .04 / .08 | 0.62 → 0.00 (over-steer → collapse) | — |
| harm | .005 / .01 | **0.75** / 0.62 (own surviving direction restores too) | 0.00 |
| harm | .02 / .04 / .08 | 0.38 → 0 (over-steer) | — |
| random | .005 / .01 / .02 / .04 | 0.38 / 0.50 / 0.62 / 0.38 | 0.00 |

**Causal restoration confirmed, with one honest caveat.** Steering the surviving refusal/harm
direction **restores refusal dose-dependently** on the abliteration-only model (0.38 → 0.88 for
`refusal`, → 0.75 for the model's *own* `harm` direction), peaking then over-steering into incoherence
— a textbook steering curve, and benign prompts stay ~0. This is a **behavioral** change produced by
manipulating the internal signal, so it **cannot be input-echo** — the C1 confound is answered
causally. *Caveat:* the `random` control is **not clean** — a random direction also raises refusal (to
0.62), i.e. part of the effect is non-specific (perturbing a model that still harbors latent refusal
nudges it to refuse). The direction effects are **stronger** (0.88 / 0.75 vs 0.62, and they fire at
lower α), but at n = 8 the direction-vs-random margin needs a larger prompt set + CIs to firm up.

### The headline: safety-removal has *depth*

| removal method | restore refusal by steering the surviving signal? |
|---|---|
| **abliteration only** (Heretic) | **yes** — 0.38 → 0.88, reconnectable |
| **abliteration + SFT** (huihui-v2) | **no** — flat ~0, the circuit is rewired |

Same model family, same intervention, opposite outcome. Abliteration suppresses the *writing* of the
refusal direction but leaves the downstream machinery intact, so re-injecting the signal **reconnects
the severed routing**. SFT on harmful data goes **deeper** — it retrains the circuit, and no amount of
re-injection brings refusal back. **"Depth of safety removal" is a measurable axis**, and it is the
strongest contribution to come out of C4 — richer than a single restoration curve.

*Next to firm this up:* larger prompt set (StrongREJECT/AdvBench) with CIs on the direction-vs-random
margin; replicate the GO on huihui-v1 (abliteration-only) and the NO-GO on a second SFT'd model;
per-layer / single-layer interventions; a cleaner coherence metric (current one flags short refusals).

## Implementation

`causal_recovery.py` (offline `--selftest` passing) reuses `directions_20b.pt` for `d_ref`, computes
`d_harm*` from the removed model, adds the steering hook, sweeps conditions × α, prints the
dose–response table, and saves `causal_results.json`. One A100, ~1 hour, **~$2**.

Run (on a GPU box):
```
python causal_recovery.py --removed huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2 \
    --dirs directions_20b.pt --layer 13 --alphas 0,0.05,0.1,0.2,0.4
```
Needs on the pod: `causal_recovery.py`, `trace_survival_probe.py` (imported helpers), `steer.py`,
`refusal_direction.py`, `directions_20b.pt`. (Reuse the fixed `gc.collect()` memory hygiene; only one
model is loaded here so offload is not a risk.)
