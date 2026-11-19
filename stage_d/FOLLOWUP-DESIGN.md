# Stage D run 1 follow-up (abliterated and heretic arms): design note

**Status: design note only. Not implemented, not frozen and not approved.** It records REVIEW-001's
recommendations (R1-02, R1-07, R1-08, R1-13, R1-21, R1-23, R1-27) for a follow-up run of the arms that run
1 left unobserved. The study scope (which of tests B, C and D are kept) is decided separately; nothing
here changes it. Before any spending, this design must be implemented, tested offline, frozen in a
separate `run1c_freeze.json` and approved in chat.

## Fixed from run 1 (must not change)

Items and item hashes, generation settings (FP8, 32,768-token context, the per-kind max-token caps that
include reasoning, temperature 0.6, top-p 0.95, top-k 20, thinking on, per-item seeds), the arm
checkpoints and revisions, and the scoring rules in `score_run1.py`, including pre-scoring fixes D-01
and D-02. Same GPU SKU (A100 SXM 80GB) and vLLM 0.33.0.

## Design

1. **One arm per pod session.** Each session has its own cap, its own approval and its own hard stop.
   Order: abliterated first, then heretic.
2. **Pinned environment** (R1-08). Install from a constraints file. Run `pip freeze > env.txt` on the pod
   and download it. Record the resolved Hub commit hashes (from `huggingface_hub`) for the model,
   tokenizer and both judge repositories (`unsloth/gemma-2b`, `qylu4156/strongreject-15k-v1`). Pin the
   judge revisions in the follow-up freeze.
3. **Incremental, resumable generation** (R1-02).
   - Shuffle all items by `sha256("run1c:" + id)` and split them into shards of about 250 items.
   - For each shard: run step 1, then that shard's InjecAgent step 2. Write `<arm>/shard-NNN.jsonl`,
     fsync it, then write `shard-NNN.done` containing its SHA-256.
   - On restart, skip completed shards.
   - **Partial-arm rule, chosen before launch.** Either (a) score the completed shards as a random
     subsample with stated denominators, or (b) keep the frozen rule that an unfinished arm is unobserved
     and use the shards only to resume on a new pod. Option (b) keeps run 1's rule unchanged and is the
     default unless an amendment says otherwise.
   - `score_run1.py` reads a single `<arm>.jsonl` plus `<arm>.done`. A separate, frozen assembly step
     must concatenate the completed shards, check the shard hashes and full coverage, and only then write
     `<arm>.done`.
4. **Pull as you go.** Each launcher poll downloads newly completed shards (a tar of new files only), so a
   hard stop loses at most one shard.
5. **Measured abort rule.** After the first two shards, project the finish time from measured tokens per
   second. If the projected finish is past the soft stop (hard stop minus 8 minutes), stop and record
   "insufficient time" before spending the rest. This is decided on timing alone.
6. **Cost plan from measurements** (R1-21). Use run1b's `step1_seconds` (7,382.6 s for 5,146 aligned
   requests) and its summed completion tokens. Assume ablated arms may generate more.
7. **Judge off the critical path** (R1-07). Do not judge on the paid pod after generation. Run the
   Gemma-2B StrongREJECT judge locally in WSL on the downloaded answers. Re-judge **all three arms**,
   including run1b's aligned answers, in one pass with pinned revisions. Do not mix judge outputs from
   different runs.
8. **Retry only on load failure** (R1-13). `pod_generate.py` writes `<arm>.loaded` right after `LLM(...)`
   returns. The driver may run the pre-registered base-tokenizer retry only when that marker is absent.
   Any other failure is logged as a failure, not retried.
9. **Cross-run comparability** (R1-07). Pre-register a fixed aligned anchor subset, for example 200 items
   stratified by source and chosen by hash rank before launch. Regenerate it on the follow-up pod to
   estimate run-to-run drift. Label all contrasts with the follow-up arms as cross-run.
10. **Checkpoint deletion** (R1-23). Resolve the cache path with `huggingface_hub.scan_cache_dir()` and
    delete with `delete_revisions(...)`. Log `df -h` before and after, and fail loudly if space was not
    freed. Honour `HF_HOME` and `HF_HUB_CACHE`.
11. **No idle billing** (R1-27). The driver writes a heartbeat and has an exit trap that writes
    `DRIVER_EXIT <code>`. The launcher stops polling and terminates the pod on that line, not only on
    `ALL_DONE` or an install failure.
12. **Throughput levers that leave frozen settings unchanged** (R1-21). Set `max_num_seqs` and
    `max_num_batched_tokens` explicitly, and mix `max_tokens` kinds within shards so the tail is shorter.
    Do **not** change FP8, the context length, the token caps or the sampling settings.
13. **Freeze hygiene** (R1-03). Create a new `run1c_freeze.json` that pins `run1_freeze.json` by hash,
    plus the new launcher, driver, assembly and judge files. Never regenerate `run1_freeze.json`. Keep
    the execution log outside frozen files.
14. **Also before freeze:** commit the human-validation sampler (R1-19, D-15). Compare the arms'
    `tokenizer_config.json`, `chat_template.jinja` and `generation_config.json` at their pinned revisions
    (R1-09, D-11). Add realistic reasoning-model output formats to the InjecAgent differential test
    (R1-20). Kill the CWEval container on timeout (`docker kill`, R1-16).
