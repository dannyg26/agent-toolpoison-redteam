# Manipulation check: does the abliterated model actually have no safeguards?

This is scientific hygiene for the tool-poisoning study, **not a threat model**. Before claiming the
abliterated model resists tool poisoning *despite having no safeguards*, we confirm it really has
none. We send the **StrongREJECT small set (60 forbidden prompts)** to each model as a plain
single-turn request and measure the refusal rate.

- Dataset: StrongREJECT (Souly et al. 2024), `strongreject_small_dataset.csv` —
  https://github.com/alexandrasouly/strongreject (not redistributed here).
- Scorer: a quote-normalized refusal-keyword heuristic (a *lower bound* on compliance). This is a
  manipulation check, not a graded StrongREJECT score.
- Raw model outputs are harmful and are kept **out of this repo** (scratchpad only); scores only.

## Result (real A100 run, matched BF16 pair)

| Model | Refused | Complied | Refusal rate | Median output len |
|---|---|---|---|---|
| **safeguarded** (`unsloth/gpt-oss-20b-BF16`) | 59/60 | 1/60 | **0.98** | 38 chars |
| **abliterated** (`huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2`) | 3/60 | 57/60 | **0.05** | 4761 chars |

The safeguarded model declines almost everything with a one-line refusal; the abliterated model
answers almost everything in full. **The abliteration genuinely removed the safeguards.**

This is the control that makes the tool-poisoning finding meaningful: the abliterated model has no
safety brakes at all, yet it is *harder* to hijack via a poisoned tool description — so the
protection in the safeguarded model is not a content filter catching the attack, it is the same
obedient instruction-following that the attack exploits.

## Reproduce

```bash
# with a vLLM endpoint already serving <model>
OPENAI_BASE_URL=<url>/v1 OPENAI_API_KEY=<token> \
python strongreject_check.py --model <hf-id> --label <safeguarded|abliterated> \
    --csv strongreject_small_dataset.csv --out <scratchpad-dir>
```
