# The Trace Still Knows: What Safety Removal Does to a Reasoning Model's Chain of Thought

**Working title.** *Safety Removal Is Shallow in Reasoning Models: The Harm Representation Survives in the Chain of Thought.*

**One-sentence thesis.** When you strip refusal from a *reasoning* model so it complies with harmful requests, the model's **reasoning trace still encodes that the request is harmful** — safety removal severs the trace→output routing without erasing the trace's internal harm representation — and that surviving signal is both a mechanistic finding and a practical tamper detector that output-behavior tests miss.

---

## 1. Why this is the project (and the last one wasn't)

The previous direction (abliteration → agent tool-poisoning) died for good reasons: a near-tautological result, a toy simulated substrate, measurement-only, and a crowded field. This proposal is chosen to avoid all four:

| Failure mode last time | How this project avoids it |
|---|---|
| Near-tautological result | A **falsifiable** claim with a clean go/no-go: either the harm signal survives in the trace or it doesn't. |
| Toy/simulated substrate | Real open-weight models (gpt-oss) + real harmful/benign prompt sets. No hand-built sandbox. |
| Measurement-only | A **causal** backbone (steer the surviving direction to *restore* refusal) + a mechanistic account (representation vs routing). |
| Crowded field | Verified near-empty slice: safety-removal × reasoning-trace representations is **unoccupied** as of the Nov 2026 scan (§6). |

It also **reuses everything already built**: abliteration for gpt-oss MoE (`refusal_direction.py`), forward-hook steering (`steer.py`), harmony channel parsing (`final_channel`), and refusal-direction extraction.

## 2. Background and the gap

- **Shallow safety is established for non-reasoning models.** A harm/refusal signal persists in hidden states after fine-tuning erases surface refusals; the *routing* from that signal to refusal output is what breaks ([Any-Depth Alignment, ICLR 2026](https://arxiv.org/html/2510.18081v1); [When Safety Routing Breaks, 2026](https://arxiv.org/html/2609.01455)).
- **Reasoning models localize refusal in the trace.** Refusal in gpt-oss-20b is nearly fixed once the reasoning trace exists and builds gradually across it ([Where Do Reasoning Models Refuse?, Turing Inst.](https://arxiv.org/pdf/2507.03167)).
- **Per-token trace probing is a solved method.** Probe trajectories over reasoning tokens (max-pooled, >90% AUROC) read internal state better than an LLM judge reading the text ([Monitoring the Internal Monologue, 2026](https://arxiv.org/html/2605.18549)).
- **Safety *can* be removed from gpt-oss**, but not always by a single ablation direction — anti-refusal RL and norm-preserving / CoT-aware "uncensoring" variants exist and reach ~0% refusal while keeping benchmark performance.

**The gap (verified):** no one has asked what *removing* safety does to the **harm representation inside the reasoning trace** of a reasoning model, across removal methods, with a causal test. That is this project.

## 3. Claims we will test

- **C1 (Survival).** After safety removal (final-channel refusal ≈ 0), a linear harm probe trained on the *aligned* model still fires on the *removed* model's **analysis-channel** activations (AUROC stays high).
- **C2 (Dissociation taxonomy).** The removed model's trace falls into measurable modes — **deliberate-then-comply** (still flags harm, proceeds anyway), **go-silent** (stops reasoning about safety), or **rationalize** (argues itself into compliance) — with method-dependent rates.
- **C3 (Routing, not representation).** The behavioral change localizes to late-layer / final-channel routing, not to erasure of the mid-trace harm direction.
- **C4 (Causal recovery).** Re-steering the surviving harm direction **in the trace** restores refusal in the removed model — proving the signal is causally live, not a vestige.
- **C5 (Cross-method generality).** C1–C4 hold across ≥3 removal methods (abliteration, anti-refusal-RL/"derestricted" release, and one more), so the claim is about *safety removal*, not one recipe.

Any outcome publishes: survival (C1 true) is the flashy result; representational erasure (C1 false) is a genuine counter-result to the "shallow safety" consensus *in the reasoning regime*.

## 4. Method

**Models (verified, all BF16 safetensors / `transformers`-loadable, reasoning channel preserved, shared `unsloth/gpt-oss-20b-BF16` lineage so activations are comparable):**

| Role | Checkpoint | Removal method | Refusal (per card) |
|---|---|---|---|
| Aligned reference | `unsloth/gpt-oss-20b-BF16` | none (safeguarded base) | 100% |
| Removed — strong | `huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2` | abliteration **+ SFT on harmful instructions** | lowest (to measure) |
| Removed — moderate | `huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated` | single-direction abliteration (Sumandora) | — |
| Removed — weak (independent tool) | `p-e-w/gpt-oss-20b-heretic` | Heretic automated abliteration | **58/100** |

**Bonus finding (free, strengthens the paper): gpt-oss-20b is abliteration-*resistant*.** The best automated single-direction tool (Heretic) only drops refusals to 58/100 — consistent with "no single refusal direction" in reasoning models. This gives us a natural **removal-strength spectrum** (weak abliteration → abliteration+SFT) rather than a binary, letting us ask how the trace representation degrades *as a function of removal strength*. The two pipelines (huihui vs Heretic) are from independent authors/tools, satisfying the cross-method claim C5. (The `openai/gpt-oss-20b` original is MXFP4 and needs kernels; the BF16 variants above load as plain bf16 — the setup already validated on the pod. Harmful generations stay in scratchpad, never committed.)

**Data.** A harmful set (e.g., AdvBench/StrongREJECT-style prompts) + a matched benign set, each run through the harmony template so we get `analysis` and `final` channels per generation.

**Probes.** Train a linear harm probe per layer on the *aligned* model's activations (harmful vs benign), max-pooled over trace tokens per [Probe Trajectories]. Evaluate transfer to removed models, **separately per channel**. Primary metric: per-channel harm-probe AUROC; secondary: per-token probe trajectories.

**Behavioral.** Final-channel refusal rate (confirm ≈ 0 post-removal) via the existing `final_channel` parser.

**Taxonomy.** Label traces (deliberate-then-comply / go-silent / rationalize) with an LLM judge, validated by human spot-check on a sample; relate labels to probe firing.

**Causal.** Use `steer.py` forward hooks to add back the harm direction at trace positions and measure restored refusal (C4); ablate at final-channel positions only vs trace positions only to localize routing (C3).

## 5. Go/No-Go (week 1, ~$5 GPU)

1. Load `unsloth/gpt-oss-20b-BF16` (aligned) + `huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2` (strongest removal).
2. Confirm final-channel refusal is low on the removed model (behavioral; measured, not assumed).
3. Train the harm probe on the aligned model's analysis-channel activations; test on the removed model's analysis-channel activations.
4. **GO** if the probe still fires (AUROC ≫ 0.5) → C1 holds → full study. **Soft-go** if it collapses → pivot to the counter-result framing. The experiment is implemented in `trace_survival_probe.py` with an offline `--selftest`.

> **Week-1 result — GO (2026-11-09, A100, ~$1.40).** Aligned = `unsloth/gpt-oss-20b-BF16`, removed = `huihui-ai/…-abliterated-v2`, layer 13, n = 8 harmful + 8 benign seed prompts.
> - final-channel refusal on harmful: **aligned 1.00 → removed 0.00** (removal is behaviorally complete).
> - **analysis-channel** harm-probe AUROC (probe trained on *aligned* trace): **aligned 1.00, removed 1.00** — the harm representation is fully preserved in the removed model's reasoning trace. **C1 confirmed.**
> - final-channel AUROC on removed = `nan` (capture gap: a class had no parsed final-channel vector; the final channel is the less-interesting one and this is a fix-in-full-study detail).
>
> *Caveats before over-claiming:* n = 16 makes AUROC 1.00 easy; the full study needs StrongREJECT/AdvBench-scale prompts with CIs, per-layer trajectories, the **causal recovery test (C4)** to prove the surviving signal is causally live (not input-echo), a prompt-only-vs-trace-only control for the echo confound, and cross-method replication (Heretic, huihui-v1). But the go/no-go is unambiguous: the trace signal survives at full strength while behavior is fully decensored.

## 6. Novelty check (Nov 2026 scan)

Occupied and cited, **not** our claim: shallow-safety in non-reasoning models ([Any-Depth], [Routing Breaks]); refusal localization in reasoning traces ([Where Do Reasoning Models Refuse?]); trace probing method ([Probe Trajectories]); tamper detectors ([Google AMS](https://opensource.googleblog.com/2026/04/introducing-ams-activation-based-model-scanner-for-open-weight-llm-safety-verification.html), [checkpoint audit](https://www.emergentmind.com/papers/2607.01854)). **Unoccupied:** safety-removal's effect on the reasoning-trace harm representation, the dissociation taxonomy, and causal trace-recovery. A final arXiv/Semantic Scholar sweep precedes submission.

## 7. Risks

- **Single-direction abliteration may not cleanly remove refusal on gpt-oss** (known). *Mitigation:* rely on public removed variants + anti-refusal methods; our abliteration is one point, not the whole study.
- **Probe transfer confound** (a probe can fire on surface features). *Mitigation:* matched benign control, cross-layer trajectories, and the causal recovery test (C4) which a spurious probe cannot pass.
- **Taxonomy subjectivity.** *Mitigation:* probe-grounded labels + human validation + report judge–human agreement.
- **Scoop risk** (hot area). *Mitigation:* narrow, causal slice; move fast; the counter-result branch is a hedge.

## 8. Deliverables & rough timeline

- **Wk 1:** go/no-go (C1). **Wk 2–3:** full probes + taxonomy across methods (C2, C5). **Wk 4:** causal recovery + routing localization (C3, C4). **Wk 5–6:** writing, final novelty sweep, ablations.
- Target: a top-tier venue (ICML/NeurIPS/ICLR) or a strong safety workshop as a fallback.

---
*Reusable assets from the prior effort: `refusal_direction.py` (direction extraction + MoE-aware abliteration), `steer.py` (hooks + `final_channel`), harmony tooling. The agent sandbox is not used.*
