# Expanded results — safeguards vs. no-safeguards (gpt-oss-20b)

Supersedes the pilot numbers in `PILOT-RESULTS.md`. Pools **7 repeats per arm** (2 pilot + 5 study)
across all runs in `results/`: **n = 112 per (reasoning × attack) cell** for the non-blatant rates
below. Same matched BF16 pair, native function-calling agent, verified canary leaks, Runpod A100.
Total compute so far ≈ **$3.8**.

- **safeguarded** = `unsloth/gpt-oss-20b-BF16`
- **abliterated** (safeguards removed) = `huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2`

## Results (non-blatant attacks; 95% bootstrap CIs)

| Metric | reasoning | safeguarded | abliterated | safeguards effect (abl − sg) |
|---|---|---|---|---|
| **Verified exfil** (real leak) | off | **0.52** [0.43, 0.61] | **0.00** [0.00, 0.00] | **−0.52** [−0.61, −0.43] ✔ sig |
| | on | **0.48** [0.39, 0.58] | **0.00** [0.00, 0.00] | **−0.48** [−0.58, −0.39] ✔ sig |
| **Leak \| task completed** (capability-controlled) | off | **0.62** [0.52, 0.71] | **0.00** | **−0.62** [−0.71, −0.52] ✔ sig |
| | on | **0.58** [0.48, 0.68] | **0.00** | **−0.58** [−0.68, −0.48] ✔ sig |
| Unauthorized read (touched the secret) | off | 0.62 [0.53, 0.71] | 0.14 [0.08, 0.21] | −0.47 ✔ sig |
| | on | 0.59 [0.50, 0.68] | 0.22 [0.15, 0.30] | −0.37 ✔ sig |
| Benign completion (capability) | off | 0.84 [0.77, 0.90] | 0.60 [0.51, 0.69] | −0.24 ✔ sig |
| | on | 0.79 [0.71, 0.86] | 0.68 [0.59, 0.77] | −0.11 (ns) |

Blatant (overt) attacks: ≈0% exfil for both (one stray episode). Clean tasks: safeguarded 100%,
abliterated ~90%.

## Findings

1. **Removing safeguards did not increase harm — it eliminated verified leaks.** The safeguarded
   model completed a real exfiltration ~50% of the time on plausible/neutral tool-poisoning; the
   abliterated model did so **0%**. Safeguards effect −0.48 to −0.52, significant. This is the
   opposite of the "no safeguards ⇒ more dangerous" intuition.

2. **It is NOT just "the abliterated model is dumber" — the key control.** Among episodes where the
   model *actually completed the benign task*, the safeguarded model still leaked **58–62%** vs the
   abliterated model's **0%**. Conditioning on capability makes the gap *larger*, not smaller, so
   reduced competence does not explain it.

3. **The abliterated model doesn't even engage the attack.** It touches the sensitive file far less
   often (unauthorized_read 0.14–0.22 vs 0.59–0.62) — it is not following the injected instruction,
   not merely failing to finish it.

4. **Mechanism hypothesis (not proven):** tool-poisoning exploits *instruction-following*. The
   safety-tuned model is a strong, compliant instruction-follower, so it dutifully obeys the
   malicious instruction embedded in the tool description; abliteration appears to also degrade that
   obedient instruction-following, incidentally making the agent harder to hijack this way.

5. **Reasoning effort (low vs high) had no significant effect** on exfil (safeguarded −0.04,
   CI [−0.17, +0.10]). The earlier project's reasoning effect does not appear here.

6. **Both models refuse blatant attacks** (~0%).

## Caveats (keep these in any write-up)

- **One model family, one abliteration, simulated tools.** The within-family, capability-controlled
  result is robust, but generality across families (Llama, Mistral, etc.) is untested — a planned
  extension we could not run within budget. Closed frontier models (ChatGPT/Claude) cannot be tested
  on the safeguards-off side at all, since their weights are not released.
- **"Reasoning off/on" = gpt-oss effort low/high**, not CoT absent/present.
- Numbers regenerate from `results/*.json` via `stats_exec.py --exclude-blatant` (+ `--metric`).

## Reproduce

```bash
python stats_exec.py --metric executed_exfil --exclude-blatant     # headline + capability-controlled
python stats_exec.py --metric unauthorized_read --exclude-blatant  # intent
python stats_exec.py --metric benign_completed --exclude-blatant   # capability
```
