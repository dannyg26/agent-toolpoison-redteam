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

## Attempt 4 (2026-11-16, A100 PCIe, pod tket5gsjf695r9, commit 2e7c5b4)

**What worked.** Fix A2: setup, the pre-flight checks, the simulated user and the abliterated checkpoint
all succeeded.

**What failed.** `bfcl generate` then hung. In `--skip-server-setup` mode it waits for the server by
polling `/v1/models` **without** an API key, and the key-protected server answered `401 Unauthorized`
every time. BFCL never sent a test case, and no benchmark item was attempted. After 30 minutes with an
unchanged log and an idle GPU, the watcher's stall rule stopped the run and terminated the pod. Cost about
$1.52.

**Fix A3.**
- **No server key.** The vLLM servers run without `--api-key`. They listen only on `127.0.0.1` inside the
  pod, so the key gave no protection. The `/v1/models` record of the served model is still saved.
- **Faster stall rule.** The watcher's stall limit drops from 30 to 15 minutes. The watcher runs locally
  and is not part of the repository.
- **Unchanged:** the gate, tasks, checkpoints, precision and context length.

## Attempt 5 (2026-11-16/17, A100 SXM, pod zz3t3fhor4iyg0, commit db9e922)

**What worked.**
- Fix A3: setup, the pre-flight checks and both servers succeeded.
- BFCL on the abliterated checkpoint ran all 221 cases and scored (exit 0, 29 minutes).
- τ-bench airline finished, and retail reached 9 of 10.

**How it ended.** At 01:24 local the pod stopped answering. RunPod then reported it as not found, and the
watcher's terminate call had nothing left to stop. The balance was not exhausted ($10.01 afterwards), so the
cause is on RunPod's side and unknown. The outputs had been copied back before it disappeared. The aligned
checkpoint never ran. Cost about $5.30.

**The τ-bench results are invalid** and are not scored, because of two integration faults:
- **Tool calls were never parsed.** Through vLLM's chat endpoint, Qwen3.8's own chat template has the model
  write tool calls in Qwen's XML form (`<tool_call><function=…><parameter=…>`). The server's `hermes` parser
  expects JSON, so it failed on every call (9,552 parser errors in the log). All 143 tool calls the agent
  wrote in airline and retail stayed as plain text, and the environment executed none. The 5 airline tasks
  scored 1 needed no database change. BFCL was unaffected: its Qwen handler writes the prompt itself and
  asks for JSON inside `<tool_call>`, and 1 of 221 outputs failed to decode.
- **τ-bench 2.0's graders call OpenAI by default.**
  - Airline's `COMMUNICATE` check uses an LLM judge, `gpt-5.5`, unless `--communicate-scorer` or
    `--communicate-judge` is given.
  - Retail's `NL_ASSERTION` check uses `gpt-5.4-mini`, fixed in `tau2/config.py` with no command-line
    option.
  - With no OpenAI key, 5 tasks (airline 3 and 7, retail 67, 89 and 113) ended in `infrastructure_error`.
  - Telecom grades with environment assertions and actions only, so it needs no judge.

**Partial BFCL result (abliterated, reported, not a gate result).** Official accuracy per category:

| category | accuracy | category | accuracy |
|---|---|---|---|
| `simple_python` | 20/20 | `live_simple` | 17/20 |
| `multiple` | 20/20 | `live_multiple` | 17/20 |
| `parallel` | 15/20 | `live_parallel` | 14/16 |
| `parallel_multiple` | 19/20 | `multi_turn_base` | 13/15 |
| `irrelevance` | 8/20 | `live_irrelevance` | 13/20 |
| `multi_turn_miss_param` | 10/15 | `multi_turn_miss_func` | 8/15 |

**Fix A4** (`run_stage_a.sh`):
- **Parser:** `--tool-call-parser qwen3_coder`, the vLLM parser for this XML form, for all three servers.
- **Pre-flight:** check that the installed vLLM registers that parser.
- **Tool check after each server starts:** one chat request offering a tool. The run stops unless the
  server returns a parsed call with arguments. This would have caught the fault in minutes.
- **Unchanged:** the gate, task lists, checkpoints, precision, context length and BFCL path.
