# Study plan — from where we are to a submittable paper, fast

Companion to `PROPOSAL.md` and `CAUSAL-TEST.md`. Goal: **finish a real paper soon** without betting
everything on a giant experiment matrix.

## SCOPE LOCK (decided 2026-11-09 — read first, resist drift)

**The paper, one sentence:** *In reasoning models, abliteration removes refusal behavior but leaves the
harm representation intact in the chain of thought — and that signal is causally reconnectable (steering
restores refusal), whereas SFT-based removal rewrites the circuit and is not.*

**IN — this is the whole paper; nothing else gets added until a draft exists:**
- **Exactly 3 reasoning families, small models** (family diversity, not size, is what proves generality):
  1. `gpt-oss-20b` (OpenAI/harmony channels) — have it, + its abliterated + its abliteration+SFT variant.
  2. `Qwen3-4B-Thinking` (Qwen arch, `<think>`) — + huihui abliterated-only variant.
  3. `DeepSeek-R1-Distill-Llama-8B` (Llama arch, `<think>`) — + an abliterated-only variant.
- **Exactly 3 results:** (C1) survival — harm-probe AUROC in the trace, per family, with CIs;
  (C4) causal reconnection — direction beats random, CI excludes 0, per family; (depth contrast) —
  abliteration reconnectable vs SFT not, on gpt-oss (the one family where we have both).
- **Stats:** bootstrap CIs + multi-seed random control — the E1 harness, already built.
- **Target:** one workshop paper. Then **stop experimenting and write.**

**OUT — explicitly, to stay on one thesis:**
- The old tool-poisoning / injection-resistance project (dead — a different paper).
- Non-reasoning models (Gemma, Mistral) — off-thesis; they test an already-answered question.
- 30B+ models, per-layer sweeps, extra SFT models, extra interventions — conference-version polish *after* a draft.
- A 4th+ family — the model zoo is exactly the drift we're refusing.

**STOP condition:** once the 3-family table (C1 + C4 + depth contrast, with CIs) exists → freeze
experiments and write. Everything below serves only this.

## Target venue (the "soon" move)

- **Near-term: a workshop paper.** A NeurIPS / ICLR **interpretability or safety workshop** is the
  realistic finish-soon target — ~4–8 pages, preliminary-but-rigorous results are expected and welcome,
  fast review, and it's a citable artifact you can show your advisor now. This is the fastest honest
  path to "done."
- **Stretch: extend to a main-track conference** (ICML / NeurIPS / ICLR) once the full matrix is in.

The workshop version needs **E1–E2 solid + E3 as a two-point contrast + a clean write-up.** Everything
else (E4, more models) upgrades it toward the conference version.

## What we have (don't re-do)

- **C1 (survival):** harm probe trained on the aligned trace fires at AUROC 1.00 on the decensored
  model's trace while refusal = 0%. ✅ go/no-go passed (n=16).
- **C4 (causal recovery):** steering the surviving direction restores refusal 0.38→0.88 on
  abliteration-only (Heretic), fails on SFT'd (v2) → **depth-of-removal** contrast. ✅ go/no-go passed
  (n=8), **one caveat**: random control not clean.

## The minimum result set, in priority order

**E1 — Scaled C4 causal control (DECISIVE — build + run first).**
The one number that sets the paper's strength: does the refusal/harm direction beat a random direction
at scale, with confidence intervals? Upgrades over the go/no-go:
- Real benchmark prompts: ~60 harmful (StrongREJECT or AdvBench subset) + ~60 matched benign.
- **Bootstrap 95% CIs** on every rate and on the **direction-minus-random margin** (the key quantity).
- **Multi-seed random control** (≥5 random directions averaged) so "random" is a fair baseline, not one draw.
- Fixed coherence metric (separate *refusal* from *gibberish* — current gate wrongly flags short refusals).
- Outcome: if the direction-vs-random margin's CI excludes 0 → **specificity holds, C4 is strong.** If it
  includes 0 → C4 narrows to "perturbation induces caution," and the paper leans on C1 + depth contrast.

**E2 — Scaled C1 survival.** Same benchmark prompts; per-layer probe AUROC with CIs, aligned vs removed,
per channel. Adds the **prompt-only vs trace-only control** that kills the input-echo confound rigorously.

**E3 — Cross-family generalization (the headline table).** Run E1 + E2 on the **3 locked families**
(gpt-oss, Qwen3-4B-Thinking, DeepSeek-R1-Distill-Llama-8B), each aligned-vs-abliterated. Plus the
**depth contrast** on gpt-oss (abliteration-only reconnectable vs abliteration+SFT not). This table —
same finding across 3 architectures — is what makes it a paper, not a single-model note. **Then stop.**

**E4 — Rigor pass (conference upgrade).** Layer/band sweep for the intervention; single-layer vs band;
robustness of the probe direction; a second coherence check. Optional for the workshop version.

**E5 — Write-up.** Intro / related work (we already scanned the field in `PROPOSAL.md` §2, §6) →
methods → results (E1–E3 tables + dose-response figure) → limitations. Reuse the honest caveats already
recorded.

## Cost, blockers, rough timeline

- **Compute:** E1 ≈ 1 A100-hr (~$2); E2 shares loads with E1; E3 ≈ 2–3 runs (~$5). Full workshop set
  ≈ **$10–15 of GPU.** **Blocker: RunPod balance is $2.96 — top up before E1.** And **rotate the API key.**
- **Effort:** E1 build (benchmark + CIs + multi-seed + metric fix) is the main code lift; E2/E3 reuse it.
- **Timeline (focused):** E1 built + run ~ a few days; E2–E3 ~ 1–2 weeks; write-up ~ 1 week →
  **workshop-ready in ~3–4 weeks** of focused work.

## Immediate next step

Build **E1**: upgrade `causal_recovery.py` + `trace_survival_probe.py` to the scaled, CI'd,
multi-seed-control version, source the benchmark prompts, and validate offline. No GPU needed to build —
only to run. Then one run tells you how strong the paper is.
