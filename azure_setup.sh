#!/usr/bin/env bash
# One-shot environment setup for serving the gpt-oss models on an Azure GPU VM (Ubuntu + NVIDIA).
# Run it ON the VM, from inside this repo:  bash azure_setup.sh
set -euo pipefail

echo "== 1. GPU check =="
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "!! nvidia-smi not found. Install the NVIDIA driver first:"
  echo "   Azure Portal -> your VM -> Extensions -> add 'NVIDIA GPU Driver Extension', OR"
  echo "   use the 'NVIDIA GPU-optimized' marketplace image, then re-run this script."
  exit 1
fi
nvidia-smi --query-gpu=name,memory.total --format=csv

echo "== 2. System packages =="
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip git tmux

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
echo "Next (see AZURE.md for details):"
echo "  1) Serve a model in one tmux pane, e.g.:"
echo "       vllm serve unsloth/gpt-oss-20b-BF16 --port 8000 --enable-auto-tool-choice"
echo "  2) In another pane, run the benchmark:"
echo "       export OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=EMPTY"
echo "       python run_agents.py --models 'safeguarded=unsloth/gpt-oss-20b-BF16' \\"
echo "         --reasoning-toggle gptoss_effort --framing all --repeats 4 --include-clean"
echo "  3) Swap to the abliterated model and repeat, then: python stats_exec.py"
echo
echo "!! When finished, DEALLOCATE the VM in the Azure Portal (Stop) so billing stops."
