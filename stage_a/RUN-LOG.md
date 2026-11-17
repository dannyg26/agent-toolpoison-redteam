# Stage A run log

Integration fixes on the development tasks, as `GATE.md` allows. Each is logged before the rerun. None
changes the gate criteria, the task lists or the checkpoints.

## Attempt 1 (2026-11-16, A100 SXM, pod w83i0jgarjzapm)

Stopped before any GPU work. The local launcher passed a bare commit ID to `git bundle`, which needs a ref.
Fixed in the launcher, which is not part of the repository. Cost about $0.

## Attempt 2 (2026-11-16, A100 PCIe, pod xrzioxgtf5mkig, commit aad2378)

**What worked.**
- Setup succeeded and the BFCL adapter applied.
- Revisions were pinned in `revisions.txt`:
  - abliterated `739e3c5b`;
  - aligned `37561816`;
  - simulated user (FP8) `c3a462cc`.

**What failed.** Serving the simulated user. The weights loaded (28.8 GiB), but at
`--gpu-memory-utilization 0.42` the KV cache had −0.81 GiB available, so vLLM refused to start. No model
under test was served and no benchmark ran. Cost about $0.92.

**Fix A1** (`run_stage_a.sh`, applied to both servers identically):
- **Text-only serving:** `--limit-mm-per-prompt '{"image":0,"video":0}'`. Qwen3.8 is a vision-language
  model and the benchmarks are text-only, so this stops vLLM reserving memory for the unused vision encoder.
- **`--max-num-seqs 32`.**
- **Memory shares:** 0.45 for the simulated user and 0.47 for the checkpoint under test, together 0.92 of
  the GPU.
- **Unchanged:** precision (FP8), context length (32,768) and every gate setting.

## Attempt 3 (2026-11-16, A100 PCIe, pod kxhq5gwzgw929v, commit 3341b00)

**What worked.** Fix A1: all three models served, the simulated user in 11 minutes including downloads and
each checkpoint in about 5 minutes.

**What failed.** Both benchmarks exited within seconds, so no benchmark item was attempted and no score
exists. Cost about $0.87.

- **BFCL** failed at import. BFCL's Qwen API handler imports `qwen_agent`, which needs `soundfile`, and
  that was not installed.
- **τ-bench was the wrong package.** The runner installed the PyPI package named `tau2` (4.0.1), which is
  an unrelated physics tool for magnetic relaxation. The name and release date had been mistaken for
  τ-bench. It only printed its help. The plan's note naming it is corrected.
- **The runner kept going after the failures** and reported ALL_DONE.

**Fix A2** (`run_stage_a.sh`):
- **BFCL:** install `soundfile` alongside `bfcl-eval==2026.3.23`.
- **τ-bench:** install from `github.com/sierra-research/tau2-bench` at tag `v2.0.0` (commit `989d3285`),
  editable, in a Python 3.12 environment from `uv`, since the benchmark needs Python 3.12 or newer. The
  frozen 30 task IDs were checked to be in that release's `train` split.
- **Pre-flight checks before any model download:**
  - BFCL imports with both adapter entries present;
  - `bfcl generate` accepts `--run-ids`;
  - `tau2 run` accepts `--task-ids` and `--user-llm`;
  - the three domains' task data exists.
- **Fail fast.** A non-zero exit from either benchmark now stops the run with a FAILED line.
- **Keys.** τ-bench gets the server key through `api_key` in the LiteLLM arguments as well as the
  environment. It is a temporary key that exists only on the pod.
- **Unchanged:** the gate criteria, task lists, checkpoints and serving settings.
