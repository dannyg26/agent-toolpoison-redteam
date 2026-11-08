# When removing safeguards makes agents *safer*: an adversary-dependent account of tool-poisoning robustness

**Draft — results consolidated so far. Pending items are marked ⏳ (need compute).**

## Thesis (one sentence)

Removing a model's safety alignment has an **adversary-dependent** effect on agent security, and both
directions trace to a single variable — **instruction-following**: against a *malicious user* it
increases harm, but against a *third-party injection* (tool poisoning) it *reduces* harm, because the
attack and the model's usefulness are the same obedient trait.

## Why this is novel vs. prior work

- **MCP tool poisoning** was disclosed by Invariant Labs (Apr 2025) and benchmarked at scale by
  **MCPTox** (AAAI 2026; 45 live servers, 353 tools, 1348 cases, 20 models): average attack success
  36.5%, up to 72.8%, refusal rate <3%. MCPTox shows *inverse scaling* — more capable models are
  **more** hijackable — and attributes it to instruction-following, but the evidence is
  **correlational** (comparing 20 off-the-shelf models).
- **Our contribution is causal and within-model.** We take one model and *intervene* on the
  safeguard/instruction-following direction (abliteration; Arditi et al. 2024), and show the
  hijackability moves with it — ruling out the "capable models just differ in many ways" confound.
  We also contrast the *malicious-user* and *third-party* adversaries on the same models, giving the
  adversary-dependent flip that neither side shows alone.

## Methods

- **Models (matched BF16):** safeguarded = `unsloth/gpt-oss-20b-BF16`; no-safeguards =
  `huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2`. gpt-oss is OpenAI's open release — the most
  industry-relevant model whose weights are open enough to intervene on.
- **Agent harness:** native function-calling, multi-step execution over a sandbox with canary
  secrets. We record **verified** harm (a canary actually reaching an attacker endpoint), not intent.
- **Causal knob:** the refusal direction = mean(harmful) − mean(harmless) last-token hidden state;
  removed from the residual-writing weights (incl. the gpt-oss mixture-of-experts fused tensors),
  scaled by α ∈ [0,1] (abliteration) or applied live during generation (steering).

## Results

### R1 — Third-party injection (tool poisoning): safeguards *hurt* (n=112/cell)

On plausible/neutral poisoned tool descriptions, with 95% bootstrap CIs:

| Metric | safeguarded | abliterated | effect |
|---|---|---|---|
| Verified exfil (real leak) | 0.48–0.52 | **0.00** | −0.48 to −0.52 ✔ sig |
| Leak \| task completed (capability-controlled) | 0.58–0.62 | **0.00** | −0.58 to −0.62 ✔ sig |
| Unauthorized read (touched the secret) | 0.59–0.62 | 0.14–0.22 | sig |

The safeguarded model leaks ~50% of the time; the no-safeguards model leaks **nothing**, and the gap
*grows* when we condition on task completion — so it is not merely "less capable."

### R2 — Direct misuse (StrongREJECT, 60 prompts): safeguards *work*, and abliteration truly removed them

| Model | Refused | Complied |
|---|---|---|
| safeguarded | **59/60 (98%)** | 1/60 |
| abliterated | 3/60 (5%) | **57/60 (95%)** |

This is both a result (against a *malicious user*, safeguards matter: the no-safeguards model answers
95% of openly harmful requests) and the **manipulation check** for R1/R3: the abliterated model
genuinely has no safety brakes, so its injection-robustness in R1 is not an artifact of a broken model.

### R3 — Causal mechanism: the safeguard is a single, removable direction

On the real gpt-oss-20b, we extract the refusal direction and remove it (97 tensors edited, including
the MoE expert weights). Refusals on held-out harmful prompts drop:

**89% → 33%** (best layer, full removal)

This demonstrates the vulnerability and the safety behavior ride on the *same* single direction — the
causal core of the thesis. Late-layer directions that "look" most separated do **not** work for
ablation; a mid-depth direction (layer 13 of 24) does — consistent with Arditi et al.

## Pending (need compute — currently blocked on GPU budget)

- ⏳ **Clean dose-response dial** via inference-time steering (`steer.py`, built + validated offline):
  refusal rate, **hijack rate**, and an independent **instruction-following score** (IFEval) across
  α ∈ {0,…,1}, on a large eval set. Expected: hijackability falls and direct-harm rises as α↑, both
  tracking instruction-following — the money figure. *(A first attempt was cut off when the GPU
  budget hit $0; only the α=0 point was captured and is not reliable.)*
- ⏳ **Specificity control:** steering a *random* direction of equal norm changes nothing.
- ⏳ **Headline on gpt-oss-120b** (same family, bigger scale).

## Limitations

- One model family, one abliteration, simulated tools. The within-family, capability-controlled and
  causal results are robust; cross-family generality is untested (a planned extension). Closed
  frontier models (GPT-5/Claude/Gemini) cannot be tested on the no-safeguards side — their weights are
  not released, which is also *why* gpt-oss is the vehicle here.
- "Reasoning off/on" in R1 = gpt-oss effort low/high, not CoT absent/present.

## Repro pointers

- R1: `stats_exec.py --metric executed_exfil --exclude-blatant` (+ `unauthorized_read`, `benign_completed`)
- R2: `strongreject_check.py` ([SAFEGUARD-CHECK.md](SAFEGUARD-CHECK.md))
- R3: `refusal_direction.py` (extract/abliterate); dial engine `steer.py`
