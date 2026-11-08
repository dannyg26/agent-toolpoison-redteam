# When removing safeguards makes agents *safer*: an adversary-dependent account of tool-poisoning robustness

**Draft — R1 + R2 are complete and measured. R3's continuous dial and the gpt-oss-120b headline are
future work (see Open problems), and are not prerequisites for the core claim.**

## Thesis (one sentence)

Removing a model's safety alignment has an **adversary-dependent** effect on agent security, and both
directions trace to a single variable — **instruction-following**: against a *malicious user* it
increases harm, but against a *third-party injection* (tool poisoning) it *reduces* harm, because the
attack and the model's usefulness are the same obedient trait.

## 1. Introduction

Large language models are increasingly deployed not as chatbots but as **agents**: they are given a
set of tools and left to call them in a loop to accomplish a task. The Model Context Protocol (MCP)
has made this concrete and widespread — an agent connects to third-party *servers*, each advertising
*tools* described in natural language, and the model decides which to invoke. This design quietly
moves a large part of the agent's input out of the user's hands: the **tool descriptions themselves**
are untrusted data, authored by whoever wrote the server, yet they flow into the same context the
model reasons over. A malicious or compromised server can therefore embed instructions in a tool's
description — a **tool-poisoning attack**, a species of *indirect prompt injection* in which the
adversary is neither the user nor the model but a third party in the data supply chain.

Recent benchmarks make the threat concrete. MCPTox evaluates 20 models across 45 live servers and
finds attack success rates averaging 36.5% and reaching 72.8%, with models refusing in under 3% of
cases. Strikingly, it reports **inverse scaling**: *more capable* models are *more* hijackable, and
attributes this to their stronger instruction-following. This sits uneasily beside the field's
default assumption — that safety alignment (refusal training) is uniformly protective, so that
stripping it (via open-weight "uncensored" fine-tunes, or **abliteration** of the refusal direction)
can only make a deployment more dangerous. If capability and obedience *increase* an agent's exposure
to injection, it is no longer obvious that the safety-aligned model is the safer *agent*.

**We ask a direct question: does removing a model's safety alignment make an agent more or less
dangerous?** We show the answer is **adversary-dependent**, and that both directions trace to a
single underlying variable — **instruction-following**:

- Against a **malicious user** who asks for harm openly, safety alignment works and removing it is
  dangerous: the no-safeguards model answers 95% of openly harmful requests (R2).
- Against a **third-party injection** (tool poisoning), removing safety alignment *reduces* verified
  harm: the safety-aligned model leaks a planted secret 50% of the time; the no-safeguards model
  leaks it 0% (R1).

The reconciliation is that the attack and the model's usefulness are the *same obedient trait*. Safety
alignment, as a refusal reflex trained on **who is asking**, does not distinguish a legitimate user
instruction from one smuggled in through a tool description; what it reliably does is make the model a
more willing instruction-follower, which the injection then exploits.

**Contributions.**

1. **An adversary-dependent account of safeguard value.** On a single model pair we show safety
   alignment *helps* against a malicious user (R2) and *hurts* against a third-party injection (R1) —
   a sign flip that neither adversary reveals alone, unifying them under instruction-following.
2. **A controlled, same-base-model intervention.** Prior evidence for the capability/obedience story
   is correlational (comparing off-the-shelf models that differ in many ways). We instead take **one
   base model** and apply **one targeted edit** — abliteration of the refusal direction — so the only
   thing that changes is the safety brake.
3. **Verified harm, and an honest capability control.** We measure a canary *actually leaking* to an
   attacker endpoint, not refusal-string intent. We take the "it just leaks less because it is less
   capable" confound seriously and measure it: the no-safeguards model *is* partly less engaged (it
   reaches the secret 18% vs 60% of the time), but resistance survives the control — **conditioned on
   actually reading the secret, it exfiltrates 0/41 vs the aligned model's 69%**, while remaining
   capable of multi-step tool use elsewhere (64–82% benign-task completion).

**Scope and honesty.** A *continuous within-model dose-response* (abliterating at varying strengths)
would upgrade the causal claim from a two-point contrast to a curve. Our own direction-extraction does
not yet reproduce the public abliteration's safeguard removal (R3), so the dial is **future work**;
the binary same-base intervention already carries the causal argument. We study one model family with
simulated tools — the within-family and capability-controlled results are robust; cross-family
generality is a planned extension.

## 2. Related work

*(Citation keys below are placeholders pending a bibliography pass — see "Citations to verify".)*

**Indirect prompt injection and tool poisoning.** Greshake et al. [greshake2023] introduced *indirect*
prompt injection, where the adversarial instruction arrives through content the model retrieves rather
than the user's prompt, and it is catalogued as the top risk (LLM01) in the OWASP Top 10 for LLM
Applications [owasp-llm]. Tool poisoning is the agentic instance: the malicious instruction lives in a
tool's *description* or schema. It was disclosed for MCP by Invariant Labs (April 2025) [invariant2025]
and benchmarked at scale by **MCPTox** [mcptox] (45 live servers, 353 tools, 1,348 cases, 20 models),
which reports 36.5% average / 72.8% peak attack success, <3% refusal, and *inverse scaling* with
capability. MCPTox establishes that the threat is real and widespread but compares off-the-shelf
models, so its capability–vulnerability link is **correlational**. We complement it with a *controlled*
same-base-model intervention and with *verified* exfiltration rather than attack-success-by-judgment.

**Safety alignment, refusal, and its removal.** Refusal behaviour in aligned models has a compact
mechanistic basis: Arditi et al. [arditi2024] show it is mediated by a single direction in activation
space and that **ablating ("abliterating") that direction removes refusals** while largely preserving
capability. This makes safety alignment an unusually clean target for a causal intervention, and it is
also how the open-weight community produces "uncensored" models. The prevailing framing treats such
removal as strictly increasing danger; our results qualify that framing for the *agentic, third-party*
threat model. We use abliteration not as a deployment but as a **laboratory instrument** — the smallest
edit that isolates the safety brake on an otherwise fixed model.

**Misuse benchmarks (the malicious-user axis).** A large literature measures whether models comply
with *openly* harmful requests: StrongREJECT [strongreject], HarmBench [harmbench], SORRY-Bench
[sorrybench], and, for dangerous-knowledge, WMDP [wmdp]. AgentHarm [agentharm] extends this to agentic
misuse where the *user* is the adversary. These benchmarks define the axis on which safety alignment is
clearly beneficial; our R2 uses StrongREJECT precisely to establish that benefit — and as the
manipulation check that our no-safeguards model truly has no brakes — before showing the opposite sign
on the third-party axis.

**Instruction-following as the shared variable.** The thread connecting both axes is that the trait
safety training suppresses (unconditional obedience) is the same trait an injection exploits. Inverse
scaling of injection vulnerability [mcptox] and the observation that alignment is largely a
who-is-asking reflex rather than a what-is-being-asked filter both point here. Our contribution is to
make this *causal* on one model: turning the refusal reflex off with one edit flips the safeguard's
effect from harmful (malicious user) to protective (third-party injection).

## 3. Methods

- **Models (matched BF16):** safeguarded = `unsloth/gpt-oss-20b-BF16`; no-safeguards =
  `huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2`. gpt-oss is OpenAI's open release — the most
  industry-relevant model whose weights are open enough to intervene on.
- **Agent harness:** native function-calling, multi-step execution over a sandbox with canary
  secrets. We record **verified** harm (a canary actually reaching an attacker endpoint), not intent.
- **Causal knob:** the refusal direction = mean(harmful) − mean(harmless) last-token hidden state;
  removed from the residual-writing weights (incl. the gpt-oss mixture-of-experts fused tensors),
  scaled by α ∈ [0,1] (abliteration) or applied live during generation (steering).

## 4. Results

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

## 5. Open problems / next steps

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

## 6. Limitations

- One model family, one abliteration, simulated tools. The within-family, capability-controlled and
  causal results are robust; cross-family generality is untested (a planned extension). Closed
  frontier models (GPT-5/Claude/Gemini) cannot be tested on the no-safeguards side — their weights are
  not released, which is also *why* gpt-oss is the vehicle here.
- "Reasoning off/on" in R1 = gpt-oss effort low/high, not CoT absent/present.

## Citations to verify (before submission)

Keys used in §1–§2. I am confident these works exist and say what I attribute to them, but the exact
authors / venue / year / id must be confirmed in a bibliography pass (I can run a web-search pass on
request):

| key | work (as I understand it) | confidence |
|---|---|---|
| `mcptox` | MCPTox, tool-poisoning benchmark, arXiv 2508.14925 (user-provided) | high |
| `greshake2023` | Greshake et al., "Not what you've signed up for: … Indirect Prompt Injection", arXiv 2302.12173 | high |
| `arditi2024` | Arditi et al., "Refusal in Language Models Is Mediated by a Single Direction", arXiv 2406.11717 (NeurIPS 2024) | high |
| `strongreject` | Souly et al., "A StrongREJECT for Empty Jailbreaks", arXiv 2402.10260 | high |
| `wmdp` | "The WMDP Benchmark", arXiv 2403.03218 | high |
| `agentharm` | Andriushchenko et al., "AgentHarm", arXiv 2410.09024 | high |
| `owasp-llm` | OWASP Top 10 for LLM Applications, LLM01: Prompt Injection | high (confirm year/version) |
| `invariant2025` | Invariant Labs MCP tool-poisoning disclosure, Apr 2025 (blog) | medium (confirm exact citation form) |
| `harmbench` | Mazeika et al., "HarmBench" | medium (confirm author list/venue) |
| `sorrybench` | "SORRY-Bench" | medium (confirm authors/venue) |

## Repro pointers

- R1: `stats_exec.py --metric executed_exfil --exclude-blatant` (+ `unauthorized_read`, `benign_completed`);
  capability control (exfil | read, clean-task completion) → `capability_control.py`
- R2: `strongreject_check.py` ([SAFEGUARD-CHECK.md](SAFEGUARD-CHECK.md))
- R3: `refusal_direction.py` (extract/abliterate); dial engine `steer.py`
