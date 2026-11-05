#!/usr/bin/env bash
# One-shot environment setup for serving the gpt-oss models on ANY Ubuntu + NVIDIA GPU box
# (RunPod, Vast.ai, Lambda, Azure, AWS, a lab server...). Run it ON the box, inside this repo:
#   bash setup_gpu.sh
set -euo pipefail

echo "== 1. GPU check =="
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "!! nvidia-smi not found. This box has no usable NVIDIA driver."
  echo "   On RunPod/Vast/Lambda, pick a CUDA/PyTorch image (drivers preinstalled)."
  echo "   On a bare VM, install the NVIDIA driver first, then re-run this script."
  exit 1
fi
nvidia-smi --query-gpu=name,memory.total --format=csv

echo "== 2. System packages =="
if command -v sudo >/dev/null 2>&1; then SUDO=sudo; else SUDO=; fi
$SUDO apt-get update -y
$SUDO apt-get install -y python3-venv python3-pip git tmux

echo "== 3. Python venv + vLLM =="
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install "vllm>=0.10" huggingface_hub   # gpt-oss needs vLLM >= 0.10
pip install -r requirements.txt            # the benchmark client (openai)

echo
echo "== Done. =="
echo "Activate the env in new shells with:  source .venv/bin/activate"
echo
echo "Next (see RUNPOD.md / SERVE.md for details):"
echo "  1) Serve a model in one tmux pane, e.g.:"
echo "       vllm serve unsloth/gpt-oss-20b-BF16 --port 8000 --enable-auto-tool-choice"
echo "  2) In another pane, run the benchmark:"
echo "       export OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=EMPTY"
echo "       python run_agents.py --models 'safeguarded=unsloth/gpt-oss-20b-BF16' \\"
echo "         --reasoning-toggle gptoss_effort --framing all --repeats 4 --include-clean"
echo "  3) Swap to the abliterated model and repeat, then: python stats_exec.py"
echo
echo "!! When finished, STOP/TERMINATE the GPU instance so billing stops."
