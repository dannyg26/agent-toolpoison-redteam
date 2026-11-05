# Pilot results — safeguards vs. no-safeguards (gpt-oss-20b)

**Setup.** Multi-step agent (native function-calling) over the canary sandbox. Models served on a
Runpod A100 80GB via vLLM. Matched pair, same BF16 base weights:
- **safeguarded** = `unsloth/gpt-oss-20b-BF16`
- **abliterated** (safeguards removed) = `huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2`

Each: 8 tool-poisoning tasks × {plausible, neutral, blatant} framings × reasoning {low, high} ×
2 repeats, plus clean utility tasks. Reasoning toggle = gpt-oss effort low (off) vs high (on).
Verified metric: the canary's **contents** actually reaching an attacker host (not mere intent).
**Pilot scale: n = 32 per cell** for the non-blatant attack rates below (wide CIs — treat as a
signal, not a final number). Total compute cost ≈ **$1**.

## Headline numbers (non-blatant attacks; 95% bootstrap CIs)

| Metric | reasoning | safeguarded | abliterated |
|---|---|---|---|
| **Verified exfil** (real leak) | off | **0.44** [0.28, 0.59] | **0.00** [0.00, 0.00] |
| | on | **0.53** [0.34, 0.69] | **0.00** [0.00, 0.00] |
| Unauthorized read (touched the secret) | off | 0.66 [0.50, 0.81] | 0.22 [0.09, 0.38] |
| | on | 0.59 [0.41, 0.75] | 0.25 [0.12, 0.41] |
| Benign completion (capability) | off | 0.78 [0.62, 0.91] | 0.59 [0.41, 0.75] |
| | on | 0.78 [0.62, 0.91] | 0.62 [0.44, 0.78] |

Blatant (overt) attacks: **0% exfil for both models** — both refuse obvious attacks.
Clean tasks: safeguarded ~100% completed; abliterated ~50–75%.

## What the pilot shows

1. **Removing safeguards did NOT make the agent more dangerous — it made it leak *less*.** On
   plausible/neutral tool-poisoning, the safeguarded model completed a verified leak 44–53% of the
   time; the abliterated model did so **0%**. The safeguards effect (abliterated − safeguarded) is
   **−0.44 (reasoning off)** and **−0.53 (on)**, both statistically significant (CIs exclude 0).
   This is the opposite of the "no safeguards = more harm" intuition.

2. **Why: verified harm needs competent multi-step execution, which this abliteration degraded.**
   The abliterated model touches the secret far less (unauthorized_read 0.22–0.25 vs 0.59–0.66) and
   completes legitimate tasks less often (benign 0.59–0.62 vs 0.78). It often read a file or started
   the chain but did **not** complete the read→exfiltrate sequence. So "no safeguards" lowered the
   *verified-leak* rate here mainly as a side effect of reduced agentic competence/behavior change,
   not because the model became principled.

3. **Intent ≠ execution — the whole point of the harness.** An intent-only metric (did it read the
   secret / call the suspicious tool) would tell a different story than verified leaks. Measuring
   actual exfiltration is what surfaces finding #2.

4. **Reasoning (effort low vs high) had no significant effect** in this pilot (safeguarded exfil
   +0.09, CI [−0.16, +0.34]). The earlier project's reasoning effect did not replicate at this n.

5. **Both models reliably refuse blatant attacks** (0% exfil), consistent with prior work.

## Honest caveats (must stay in any write-up)

- **Pilot, not a study:** one model family, one abliteration, simulated tools, n = 32/cell, wide CIs.
- **Capability confound:** the abliterated model is somewhat less capable (benign gap −0.16 to −0.19,
  though not individually significant here). Its 0% leak cannot be cleanly attributed to "no
  safeguards" alone — reduced competence is a plausible driver. A fair study must control for
  capability (e.g., report leak rate conditioned on benign completion, add more model pairs).
- **gpt-oss reasoning caveat:** "off/on" = low/high effort, not CoT absent/present.
- Numbers are from `results/agent_*.json` in this repo; regenerate with `stats_exec.py`.

## Reproduce

```bash
python stats_exec.py --metric executed_exfil --exclude-blatant
python stats_exec.py --metric unauthorized_read --exclude-blatant
python stats_exec.py --metric benign_completed --exclude-blatant
```
