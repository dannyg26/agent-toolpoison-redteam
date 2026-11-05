# Running the study on a per-minute GPU host (RunPod) — the cheap path

Your Azure "for Students" subscription has **zero GPU quota** (A100/H100/A10/T4 all = 0), so we use a
pay-per-minute host instead. Same vLLM, same repo, same runner — you just run it on a rented GPU and
point the benchmark at `localhost`. A **pilot costs ~$2–3**; a fuller run ~$5–15. Steps below are for
**RunPod**; **Vast.ai** and **Lambda** are nearly identical.

## 1. Account + credit (your part — I can't do this)

1. Sign up at runpod.io, add a payment method, load **$10** of credit.
2. (Optional) add your SSH public key in **Settings → SSH Public Keys** for terminal access; the
   in-browser web terminal works without it.

## 2. Deploy an A100 pod

**Pods → Deploy → GPU**:
- **GPU:** **1× A100 80GB** (both BF16 models fit; ~$1.6–2/hr on-demand). An **L40S 48GB** also works
  and is cheaper.
- **Template:** a **PyTorch 2.x / CUDA 12** image (drivers + Python preinstalled).
- **Container / volume disk:** ~**100 GB** (the two BF16 checkpoints are ~40 GB each).
- Deploy, then open the pod's **Web Terminal** (or SSH in).

## 3. Get the code onto the pod

The repo is **private**, so authenticate the clone one of two ways:

```bash
# Option A — GitHub CLI device login (easiest):
#   (install if missing: type -p gh || (apt-get update && apt-get install -y gh))
gh auth login            # choose GitHub.com -> HTTPS -> device code, paste the code in a browser
git clone https://github.com/dannyg26/agent-toolpoison-redteam.git

# Option B — a Personal Access Token (github.com/settings/tokens, scope: repo):
git clone https://<YOUR_TOKEN>@github.com/dannyg26/agent-toolpoison-redteam.git
```
```bash
cd agent-toolpoison-redteam
```
(Or just make the repo public for a few minutes and `git clone` with no auth.)

## 4. One-shot setup

```bash
bash setup_gpu.sh
source .venv/bin/activate
```

## 5. Serve each model and run the benchmark

Two `tmux` panes (Ctrl-b then `"` to split): one serves the model, one runs the benchmark. Run the
two models **one at a time** on the same port.

```bash
# --- Arm A: safeguarded baseline (BF16) ---
# pane 1:
vllm serve unsloth/gpt-oss-20b-BF16 --revision <HASH> --port 8000 --enable-auto-tool-choice
# pane 2 (once pane 1 prints "Application startup complete"):
export OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=EMPTY
python run_agents.py --models "safeguarded=unsloth/gpt-oss-20b-BF16@<HASH>" \
  --reasoning-toggle gptoss_effort --framing all --repeats 4 --include-clean

# --- Arm B: safeguards removed ---  (Ctrl-c pane 1, then:)
vllm serve huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2 --revision <HASH> \
  --port 8000 --enable-auto-tool-choice
python run_agents.py --models "abliterated=huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2@<HASH>" \
  --reasoning-toggle gptoss_effort --framing all --repeats 4 --include-clean

# --- Compare, with bootstrap confidence intervals ---
python stats_exec.py --glob "results/agent_*.json" --metric executed_exfil
```

Get `<HASH>` from each model's Hugging Face **Files and versions** tab and pass the same value to
`--revision` (serve) and `@<HASH>` (runner) so the run is reproducible. First serve of each model
downloads ~40 GB — a few minutes — before it answers.

## 6. Save results, then STOP THE POD

```bash
# push results back into the repo from the pod:
git add results && git -c user.name="you" -c user.email="you@example.com" commit -m "pilot results" && git push
# or download them from the RunPod file browser.
```
Then **Stop** (keeps the disk, small charge) or **Terminate** (deletes everything, no further charge)
the pod in the RunPod console. **This is the step that controls your bill** — a running A100 charges
every minute, idle or not.

## Cheapest possible smoke test (~$1)

Before the full run, confirm the whole chain works for pennies: serve the small **MXFP4** model on a
cheaper GPU and do one tiny pass.
```bash
vllm serve openai/gpt-oss-20b --port 8000 --enable-auto-tool-choice   # fits in 16 GB
python run_agents.py --models "smoke=openai/gpt-oss-20b" --framing plausible --repeats 1
```
If that prints a summary table, the pipeline is healthy — scale up to the A100 BF16 run.
