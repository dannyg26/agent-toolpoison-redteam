# Running the study on Azure — step by step

This is the concrete Azure path. Budget ~**$5–15** for a pilot if you **deallocate the VM** as soon
as you finish. The one real gate is **GPU quota** (below) — sort that out first; it can take a day.

## 0. Prerequisites (do these before anything else)

- A **pay-as-you-go** Azure subscription. **Student/free trial subscriptions usually cannot deploy
  A100 GPUs at all** — if that's all you have, tell me and we'll use a cheaper fallback (see §6).
- **Request GPU quota** (new subscriptions start at 0):
  Azure Portal → **Quotas** → **Compute** → pick your region → search
  **"Standard NCADS_A100_v4 Family"** → request an increase to at least **24 vCPUs**. This is a free
  support request; approval can take minutes to a day.

## 1. Create the VM

Azure Portal → **Create a virtual machine**:
- **Image:** *Ubuntu Server 22.04 LTS* (or the *NVIDIA GPU-optimized* marketplace image, which ships
  with drivers — saves a step).
- **Size:** **`Standard_NC24ads_A100_v4`** (1× A100 80GB — fits both BF16 models).
- **Authentication:** SSH public key.
- **Networking:** allow **SSH (22)** only. The model server stays on `localhost`; do **not** expose
  port 8000 to the internet.
- **Disk:** add ~**100 GB** (the two BF16 checkpoints are ~40GB each).

## 2. Connect and get the driver ready

```bash
ssh azureuser@<VM_PUBLIC_IP>
nvidia-smi        # should list an A100. If "command not found", add the
                  # 'NVIDIA GPU Driver Extension' to the VM in the Portal, reboot, retry.
```

## 3. Get the code onto the VM

Easiest once this repo is on GitHub (I can push it for you):
```bash
git clone https://github.com/<you>/agent-toolpoison-redteam.git
cd agent-toolpoison-redteam
```
(Or `scp -r` the folder up from your laptop.)

## 4. One-shot setup

```bash
bash setup_gpu.sh
source .venv/bin/activate
```

## 5. Serve each model and run the benchmark

Use two `tmux` panes (Ctrl-b then " to split): one serves the model, one runs the benchmark.
Run the two models **one at a time** on the same port.

```bash
# --- Arm A: safeguarded baseline (BF16) ---
# pane 1:
vllm serve unsloth/gpt-oss-20b-BF16 --revision <HASH> --port 8000 --enable-auto-tool-choice
# pane 2 (wait until pane 1 says "Application startup complete"):
export OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=EMPTY
python run_agents.py --models "safeguarded=unsloth/gpt-oss-20b-BF16@<HASH>" \
  --reasoning-toggle gptoss_effort --framing all --repeats 4 --include-clean

# --- Arm B: safeguards removed ---  (stop pane 1 with Ctrl-c, then:)
vllm serve huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2 --revision <HASH> \
  --port 8000 --enable-auto-tool-choice
python run_agents.py --models "abliterated=huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated-v2@<HASH>" \
  --reasoning-toggle gptoss_effort --framing all --repeats 4 --include-clean

# --- Compare, with bootstrap confidence intervals ---
python stats_exec.py --glob "results/agent_*.json" --metric executed_exfil
```

Get `<HASH>` from each model's Hugging Face **Files and versions** tab and pass the same value to
`--revision` (serve) and `@<HASH>` (runner) so the run is reproducible.

## 6. Get the results off, then SHUT IT DOWN

```bash
# from your laptop:
scp -r azureuser@<VM_PUBLIC_IP>:~/agent-toolpoison-redteam/results ./results
```
Then **Azure Portal → the VM → Stop (Deallocate)**. A running A100 bills ~$3–4/hr even when idle;
*deallocated* it costs almost nothing. This is the single most important step for staying on budget.

## Cheaper / fallback options

- **No A100 quota?** Serve the safeguarded arm as MXFP4 `openai/gpt-oss-20b` on a 16GB GPU
  (`Standard_NC4as_T4_v3`) — but then it's not precision-matched to the abliterated BF16 model, so
  note that confound. For a matched pair on a smaller GPU, use the **GGUF Q4** builds of *both*
  models instead (same precision on both arms).
- **Skip Azure entirely for a smoke test:** `python test_offline.py` validates the whole pipeline
  with no GPU, and a tiny `--repeats 1 --framing plausible` run on the MXFP4 model is a ~$1 check
  that everything talks to the server before you commit to the full run.
