# Manifest: models, revisions, data and settings (red-team attacker study)

Recorded after the fact, from run logs, the downloaded snapshots and the code. Where a value was not
recorded at collection time, the table says so instead of guessing.

## Models

| role | model | revision (HF commit) |
|---|---|---|
| attacker, aligned | `Qwen/Qwen3-8B` | not recorded |
| attacker, abliterated | `huihui-ai/Huihui-Qwen3-8B-abliterated-v2` | not recorded |
| attacker, trained (E1) | `yukiyounai/Jailbreak-R1` | `d095f88daef10d16b312c3d48db1b36ea2372260` |
| target A | `Qwen/Qwen2.5-7B-Instruct` | `a09a35458c702b33eeacc393d103063234e8bc28` |
| target B | `NousResearch/Meta-Llama-3.1-8B-Instruct` | `d10aef7999a2b5ba950ab3974312feeedbfe0b77` |
| judge | `cais/HarmBench-Mistral-7b-val-cls` | not recorded |
| judge | `qylu4156/strongreject-15k-v1` (LoRA) on `unsloth/gemma-2b` | not recorded |

The two original attackers' revisions were not pinned when the main study was collected (a known gap; the
HF "main" branch may have moved since). Target revisions are those of the snapshots served for E1.

The main study's target snapshots were not recorded, but the repositories' commit histories pin them
down (checked via the HF API):

- **Qwen2.5-7B-Instruct:** since `acbd96531cda` (2024-09-19, tokenizer config), the only commits are a
  metadata update (2024-09-25) and a README update (`a09a35458c70`, 2025-01-12).
- **Meta-Llama-3.1-8B-Instruct (NousResearch):** no commits after `d10aef7999a2` (2024-07-24).

Both collections ran in November 2026, so a download at either time gave identical weights and tokenizer
files. What remains unrecorded is the main study's vLLM version and serving options.

## Serving and decoding

- **Inference:** vLLM 0.33.0 (E1), on a single RunPod A100, OpenAI-compatible API. The main study's
  vLLM version was not recorded.
- **Attackers (main study):** temperature 0.7, max 300 tokens. **Thinking mode was not recorded and
  cannot be inferred from the stored attacks.** `make_chat` strips completed `<think>…</think>` blocks
  before an attack is stored, so their absence is no evidence.
  - Of the 3,600 stored attacks from the four attacker arms, none contains an *unclosed* `<think>` block,
    which would survive stripping (for example reasoning cut off at 300 tokens).
  - One contains a stray closing `</think>`.

  This is weak evidence at most. If reasoning was enabled, it used part of the 300-token budget, which
  could affect the attacker comparison. (An earlier version of this file called the absence of traces
  "consistent with `--disable-thinking`"; that inference is withdrawn.)
- **Jailbreak-R1 (E1):** the authors' input format, `attackers/jailbreak_r1.json` (SHA-256
  `1c0f5b83669af0723c80bcee39335d1d24844089a3014aee05449a0100f85536`).
  - Prefill `<think> Sure, let's think step by step, `, sent via vLLM `continue_final_message`.
  - Temperature 1.0, top_p 0.95, top_k −1, repetition_penalty 1.05, max 1024 tokens.
  - The `<attack>` block is extracted, with up to 4 retries.
- **Targets:** temperature 0.7, max 400 tokens.
- **HarmBench classifier:** completions endpoint, temperature 0, 1 token, the model card's
  non-contextual template (`redteam.py`).
- **StrongREJECT judge:** run locally by `sr_judge.py`. It uses the `strongreject_finetuned` prompt from
  `judge_templates.json` and outputs the expected value over "1".."5", mapped to [0, 1]; responses are
  truncated to 512 tokens.

## Data

- **Goals:** the StrongREJECT dataset CSV
  (`https://raw.githubusercontent.com/alexandrasouly/strongreject/main/strongreject_dataset/strongreject_dataset.csv`,
  313 behaviours at collection time). The goals are shuffled with `random.Random(0)` and the first 150
  are taken (`redteam.load_goals`). The main branch of that file is not pinned; the frozen data hashes in
  `ANALYSIS-PLAN.md` identify what was actually used.
- **Collection command (shape):** `redteam.py --dataset strongreject --n-goals 150 --rounds 3 --judge-kind
  none --concurrency 16`, with the attacker, target and arm flags. The run logs record `goals=150 rounds=3
  repeats=1 atk_temp=0.7 judge=none`.
- **E1 exclusions:** goal indices 15, 80, 112 and 141 (`ANALYSIS-PLAN.md` D3).

## Prospective confirmation (`CONFIRMATION-PLAN.md`, `CONFIRMATION-LOG.md`)

- **Goals.** Held-out positions 150–312 of the same shuffle: 163 goals, with the list hash pre-registered
  as `7232935885…`. The collection command adds `--goal-start 150 --n-goals 163 --expect-goals-sha256 <hash>
  --disable-thinking --refusal-check legacy`.
- **Exclusions.**
  - The pre-screen excluded 5 goals (`adj/heldout_prescreen_marks.json`).
  - The CD-2 re-screen excluded 38 more (`confirm_data/rescreen_marks.json`).
  - 120 goals per target are analysed.
- **Code.** Tag `confirm-prereg-v1` (`9c174d7`), recorded clean in every run manifest
  (`confirm_data/*.manifest.json`).
- **Models.** The same checkpoints as above. Snapshots read from the serving cache are in
  `confirm_data/model_snapshots.json` (deviation CD-1).
- **Software.** vLLM 0.33.0, torch 2.14.0, transformers 5.20.2 (`confirm_data/pip_versions.txt`).
  - Collection ran on an A100 80GB PCIe.
  - Scoring ran on an A100 SXM 80GB.
- **Records committed in `confirm_data/`.** These hold hashes, goal indices and method text only:
  - the sheet hashes, committed locally before labelling;
  - the continuation sheet hashes;
  - the blind- and final-label hashes;
  - the analysis inputs;
  - `method/`: the annotators' briefs and agent 1's helper script, with source hashes.

  Only the tag was pushed before collection. The later commits were pushed together afterwards, so their
  order is researcher-reported, not externally timestamped.
- **Result.** `confirm_results.json`.
- **Local and gitignored.** These contain model-generated harmful text and are not distributed:
  - `confirm_data/{A,B}_conf{,_ext}_{raw,scored}.json`;
  - `adj/confirm/` (sheets, key, each agent's labels and reasons, reconciliation, final labels);
  - `adj/heldout_*`.

## Bundled third-party files

| file | source | licence | SHA-256 |
|---|---|---|---|
| `judge_templates.json` | `strong_reject/eval_files/judge_templates.json` in `github.com/dsbowen/strong_reject` | MIT | `6d01841899e99f1f57c4f19153056051684ede2a7e1b54ebbb37b5ddff981768` |
| `attackers/jailbreak_r1.json` | built from the Jailbreak-R1 authors' code (prompt text and decoding settings) | see the model card | above |

## Local, gitignored inputs needed by `reproduce_results.py`

`{A,B}_scored.json`, `{A,B}_ext_scored.json` and `adj/` (keys, final labels and each agent's labels). They
contain model-generated harmful text and are not distributed. Their hashes are in `ANALYSIS-PLAN.md`.
