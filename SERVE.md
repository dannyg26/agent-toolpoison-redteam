# Serving the models on a GPU (Azure / AWS / any Linux box)

The models are **self-hosted** — no inference provider serves the abliterated checkpoint — but the
server speaks the **OpenAI-compatible** API, so the runner needs no changes: just point
`OPENAI_BASE_URL` at it.

## 1. Pick a machine

| Model | GPU needed | Example instances |
|-------|-----------|-------------------|
| 20B pair in **BF16** (recommended, precision-matched) | one **A100 80GB** (BF16 weights ~42GB each) | Azure `Standard_NC24ads_A100_v4`; AWS `p4d` |
| `openai/gpt-oss-20b` in **MXFP4** (cheaper, but confounds the comparison) | one 16GB+ GPU (T4/A10) | Azure `Standard_NC4as_T4_v3`; AWS `g5.xlarge` |
| 120B pair | 2× A100/H100 80GB | Azure ND A100 v4; AWS `p4d.24xlarge` |

> **Precision note:** the abliterated model is BF16, so match it with the BF16 baseline
> `unsloth/gpt-oss-20b-BF16` (requires vLLM ≥ 0.10). The default `openai/gpt-oss-20b` is MXFP4 and
> fits in 16GB — fine for a cheap smoke test, but do not mix precisions in the real comparison.

Rent **spot / low-priority** and **shut it down when idle** — an idle A100 is the only thing that
makes this expensive. Expect roughly **$5–15 for a pilot**, **$20–40 for a full run**, at the 20B
size if you stop the box promptly.

## 2. Install and serve (vLLM)

Pin the exact Hugging Face revision with `--revision` so the run is reproducible.

```bash
pip install vllm

# A) Safeguarded baseline (BF16, precision-matched to the abliterated model):
vllm serve unsloth/gpt-oss-20b-BF16 \
  --revision <COMMIT_HASH> \
  --port 8000 --enable-auto-tool-choice

# B) Safeguards removed (serve one at a time on the same port, or use a second port):
vllm serve huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2 \
  --revision <COMMIT_HASH> \
  --port 8000 --enable-auto-tool-choice
```

Find `<COMMIT_HASH>` on each model's Hugging Face "Files and versions" tab (the commit of the
weights you downloaded). Record it; the runner stores it in every result file.

## 3. Run the benchmark against it

```bash
export OPENAI_BASE_URL=http://localhost:8000/v1
export OPENAI_API_KEY=EMPTY

# Serve the safeguarded model, then:
python run_agents.py --models "safeguarded=unsloth/gpt-oss-20b-BF16@<HASH>" \
  --reasoning-toggle gptoss_effort --framing all --repeats 4 --include-clean

# Swap to the abliterated model on the same endpoint, then:
python run_agents.py --models "abliterated=huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2@<HASH>" \
  --reasoning-toggle gptoss_effort --framing all --repeats 4 --include-clean

# Both result files land in results/; compare them:
python stats_exec.py --glob "results/agent_*.json" --metric executed_exfil
```

## 4. Cheaper alternative

If a host adds these models to an OpenAI-compatible API later, skip the GPU entirely and set
`OPENAI_BASE_URL` / `OPENAI_API_KEY` to that service — the runner is identical. (As of setup, no
provider serves the abliterated checkpoint, so self-hosting is required for the no-safeguards arm.)
