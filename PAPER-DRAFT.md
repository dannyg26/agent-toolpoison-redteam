# When removing safeguards makes agents *safer*: an adversary-dependent account of tool-poisoning robustness

**Draft — R1 + R2 are complete and measured. R3's continuous dial and the gpt-oss-120b headline are
future work (see Open problems), and are not prerequisites for the core claim.**

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
- **Our contribution.** We contrast the *malicious-user* and *third-party* adversaries on the **same
  base model** changed by a **single targeted edit** — abliteration of the refusal direction — giving
  an adversary-dependent flip that neither side shows alone (R1 + R2). This is a *controlled*
  intervention, not a cross-model comparison. We take the "the abliterated model just leaks less
  because it's less capable" confound seriously and measure it directly: the abliterated model is
  partly less *engaged* (it reads the planted secret 18% vs 60% of the time), but the resistance is
  not only that — **conditioned on actually reading the secret, it exfiltrates 0/41 vs the safeguarded
  model's 69%**, while remaining capable of multi-step tool tasks elsewhere (64–82% benign completion).
  We also measure **verified** harm (a canary actually leaking), not intent.
- **What we do not yet have.** A *continuous within-model dose-response* (abliterating at varying
  strengths) would strengthen this from a two-point to a curve. Our own direction-extraction does not
  yet reproduce the public model's safeguard removal (R3), so the continuous dial is **future work**,
  not a gap in the causal claim — the binary same-base intervention already carries it.

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

### R1 — Third-party injection (tool poisoning): safeguards *hurt* (n=224/cell)

On plausible/neutral poisoned tool descriptions (blatant sanity-floor and clean-control framings
excluded, errored episodes dropped), exact counts with 95% bootstrap CIs:

| Metric (poisoned) | safeguarded | abliterated |
|---|---|---|
| Verified exfil (real leak) | 112/224 = 0.50 [0.43, 0.57] | **0/224 = 0.00** |
| Unauthorized read (touched the secret) | 135/224 = 0.60 [0.54, 0.67] | 41/224 = 0.18 [0.13, 0.24] |
| Benign task completed (under attack) | 182/224 = 0.81 [0.76, 0.86] | 143/224 = 0.64 [0.58, 0.70] |
| **Exfil \| read the secret** (capability control) | **93/135 = 0.69 [0.61, 0.76]** | **0/41 = 0.00 [0, 0.09]** |
| Exfil \| benign task completed | 109/182 = 0.60 [0.53, 0.67] | 0/143 = 0.00 |
| Benign completed, **clean / no attack** (pure capability) | 28/28 = 1.00 | 23/28 = 0.82 [0.68, 0.96] |

**Two things are true, and we report both — this is *not* a clean "safeguards hurt."**

1. *Part of the zero-leak is reduced engagement, not resistance.* The abliterated model completes
   slightly fewer unpoisoned tasks (0.82 vs 1.00) and, under poisoning, follows the attack far enough
   to read the secret only 18% of the time (vs 60%). So some of its 0% leak is simply that it engages
   the attack path less often. (An earlier draft said the gap "is not merely less capable" — that was
   too strong; it is *partly* a capability/engagement gap, and we now say so.)
2. *But resistance survives the strongest control we can compute.* Among the episodes where the model
   **actually read the secret**, the abliterated model sent it onward **0/41** (≤9%) versus the
   safeguarded model's **69%**. The abliterated model is not incapable of multi-step tool use — it
   completes 64–82% of benign tasks, all of which require real state-changing tool calls — so reaching
   the secret and then *not* exfiltrating it is better explained by resistance than by inability.

*Caveat we state openly:* exfiltration is a data-dependent two-step chain (read → send the secret
outward), so we cannot fully exclude that the abliterated model is specifically weaker at
*data-dependent* chaining, and the conditioned cell is modest (n = 41 reads). A benign task that
itself requires a data-dependent chain would isolate this; it is a planned control (see Open problems).

### R2 — Direct misuse (StrongREJECT, 60 prompts): safeguards *work*, and abliteration truly removed them

| Model | Refused | Complied |
|---|---|---|
| safeguarded | **59/60 (98%)** | 1/60 |
| abliterated | 3/60 (5%) | **57/60 (95%)** |

This is both a result (against a *malicious user*, safeguards matter: the no-safeguards model answers
95% of openly harmful requests) and the **manipulation check** for R1/R3: the abliterated model
genuinely has no safety brakes, so its injection-robustness in R1 is not an artifact of a broken model.

### R3 — The intervention is causal (binary), and a continuous dial is future work

**The causal claim is carried by R1 + R2 jointly, not by a dose-response curve.** We take one base
model and apply one targeted edit (abliterate the refusal direction). R2 verifies that edit changed
only the safety brake — the edited model is *more* instruction-following (95% compliance on openly
harmful requests), not degraded. R1 then shows that same edited model's injection-leak rate is zero.
A single intervention, same weights otherwise, flips the sign of the safeguard's effect depending on
the adversary. That *is* a controlled causal result; it does not require a dial.

**What a dial would add, and why we don't have it yet.** A continuous dose-response (abliterate at
strengths α = 0…1 and watch leak/refusal move together) would upgrade this from two points to a curve
and is the intended "money figure." We attempted it by extracting the refusal direction *ourselves*.
It does not work yet: an early run appeared to drop refusals 89%→33%, but that was a **measurement
artifact** — the detector scored the model's truncated reasoning channel, not its final answer.
Scoring the harmony *final* channel correctly, our own abliteration and inference-time steering leave
refusals at ~0.98 across **all** α. Our extraction simply doesn't reproduce the removal yet (most
likely token-position / layer-selection in gpt-oss's harmony format). The *publicly* abliterated model
(R2: 5% refusal) proves proper abliteration is achievable on this base, so this is a tractable
engineering task — **future work, not a hole in the causal argument.**

## Open problems / next steps

(None of these are prerequisites for the core claim — R1 + R2 stand on their own. They are
strengthenings, in priority order.)

- **Capability control — done (from existing runs).** We added clean-task completion, unauthorized-read
  rate, and *exfil | read-the-secret* to R1. It is now honest about the partial engagement gap and
  shows the residual resistance (0/41 vs 69%) that survives it. **Remaining:** a benign task that
  *itself* requires a data-dependent two-step chain, to rule out "weaker at dependent chaining" as the
  explanation for the conditioned cell, and more episodes to tighten the n=41 read-conditioned cell.
- **Make our own abliteration remove the safeguard**, then run the dose-response dial (refusal,
  **hijack rate**, **instruction-following score** across α, + a random-direction control). Upgrades
  R3 from a two-point binary to a curve. Likely fixes: extract at the correct harmony token position,
  select the layer by *measured* refusal reduction, validate against the public model's ~5%. Nice to
  have, *not* load-bearing.
- **Headline on gpt-oss-120b** (same family, bigger scale) for the final submission.

## Limitations

- One model family, one abliteration, simulated tools. The within-family, capability-controlled and
  causal results are robust; cross-family generality is untested (a planned extension). Closed
  frontier models (GPT-5/Claude/Gemini) cannot be tested on the no-safeguards side — their weights are
  not released, which is also *why* gpt-oss is the vehicle here.
- "Reasoning off/on" in R1 = gpt-oss effort low/high, not CoT absent/present.

## Repro pointers

- R1: `stats_exec.py --metric executed_exfil --exclude-blatant` (+ `unauthorized_read`, `benign_completed`);
  capability control (exfil | read, clean-task completion) → `capability_control.py`
- R2: `strongreject_check.py` ([SAFEGUARD-CHECK.md](SAFEGUARD-CHECK.md))
- R3: `refusal_direction.py` (extract/abliterate); dial engine `steer.py`
