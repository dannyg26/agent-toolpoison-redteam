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
