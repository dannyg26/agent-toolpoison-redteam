# Confirmation run log and deviations

This file records what happened after the pre-registration tag `confirm-prereg-v1` (commit `9c174d7`).
Every departure from `CONFIRMATION-PLAN.md` is listed as a deviation (CD-n). Infrastructure events that
changed nothing about the data are listed as run notes.

## Collection (2026-11-13, one RunPod A100 80GB, vLLM 0.33.0)

- **Code on the pod.** The pod got the frozen tag as a git bundle, because the repository is private.
  Every run manifest records commit `9c174d7` with a clean working tree.
- **Goals.** All runs used held-out start 150 and n = 163. The goal-list hash matched the pre-registered
  `7232935885…`, checked by `--expect-goals-sha256`.
- **Settings.** Exactly as pre-registered: 3 rounds, judge-free collection, `--disable-thinking`, and the
  legacy refusal check.

**Run notes.** No model was queried in either failed attempt, and no data was produced.

1. The first launch failed before any model served. RunPod's proxy occupies port 8001. The attacker
   servers moved to ports 8500 and 8600; the frozen code and flags were not touched.
2. Phase 3 first failed before any model served. `yukiyounai/Jailbreak-R1` is a gated repository and
   needs the researcher's Hugging Face token, as in E1. It was relaunched with the token.

3. During the relaunched phases 3–4, the RunPod account balance ran out and RunPod deleted the pod. The pod
   had no persistent volume, so everything produced after phases 1–2 was lost before it was copied off:
   the Jailbreak-R1 transcripts and any scores. No phase 3–4 output was ever seen, so no outcome informed
   the rerun. The phase 1–2 files had already been copied back with their manifests. Phases 3–4 will be
   rerun on a new pod with the same tag, flags and model snapshots, and the phase 1–2 raw files will be
   uploaded for scoring.
4. The rerun of phase 3 (2026-11-15, a new A100 pod) used the same bundle, `vllm==0.33.0` and the same
   Jailbreak-R1 snapshot `d095f88d`. The phase 1–2 files were uploaded byte-identical (checked by SHA-256).
   Phase 3 finished and both transcripts were copied back. Phase 4 then never started: the run script's
   `wait` also waited on the model servers started in the same shell, which never exit. The pod sat idle
   until the balance ran out again, and RunPod deleted it. That was a bug in the run script, not in the
   frozen code, and it cost no data. Scoring is run separately, from the copied-back raw files.

**Collection** (all confirmatory arms, both targets): complete.

| target | file | arms | goals | rounds per arm | endpoint errors |
|---|---|---|---|---|---|
| A | `A_conf_raw.json` | 5 built-in | 163 | 489 | 0 |
| B | `B_conf_raw.json` | 5 built-in | 163 | 489 | 0 |
| A | `A_conf_ext_raw.json` | trained-redteam | 163 | 489 | 0 |
| B | `B_conf_ext_raw.json` | trained-redteam | 163 | 489 | 0 |

Every manifest records commit `9c174d7` (clean), goal start 150, n = 163, the pre-registered goal hash,
thinking disabled, the legacy refusal check, and vLLM 0.33.0.

## Scoring (2026-11-15, one RunPod A100 SXM 80GB)

5. The A100 80GB PCIe was out of stock, so scoring ran on an A100 SXM 80GB. That is the same GPU in a
   different board. The plan says only "one A100", so this is not a deviation. The same bundle and
   `vllm==0.33.0` were used, and all four raw files were uploaded byte-identical (checked by SHA-256).
   One upload was truncated by a dropped connection; it was resent and rechecked before scoring.
   Both judges ran as in E1: the HarmBench classifier through vLLM and the StrongREJECT fine-tuned judge.
   `rescore.py` exited 0 on all four files, and the pod was terminated right after copy-back.
   Versions: `confirm_data/pip_versions.txt` (vllm 0.33.0, torch 2.14.0, transformers 5.20.2).

Every round sent to the target has both judge scores. The transcript text in each scored file is
identical to its raw file.

| file | arm | rounds | sent to target | scored by both judges |
|---|---|---|---|---|
| A_conf | no-attacker | 489 | 489 | 489 |
| A_conf | aligned-plain | 489 | 340 | 340 |
| A_conf | abliterated-plain | 489 | 489 | 489 |
| A_conf | aligned-redteam | 489 | 489 | 489 |
| A_conf | abliterated-redteam | 489 | 489 | 489 |
| B_conf | no-attacker | 489 | 489 | 489 |
| B_conf | aligned-plain | 489 | 358 | 358 |
| B_conf | abliterated-plain | 489 | 488 | 488 |
| B_conf | aligned-redteam | 489 | 488 | 488 |
| B_conf | abliterated-redteam | 489 | 487 | 487 |
| A_conf_ext | trained-redteam | 489 | 489 | 489 |
| B_conf_ext | trained-redteam | 489 | 489 | 489 |

Rounds not sent are the attacker's own refusals, caught by the legacy refusal check before reaching the
target, as pre-registered. Labelling uses the three confirmatory arms only (abliterated-plain,
aligned-redteam, trained-redteam). The other arms are collected but not part of the confirmation.

**Budget.** D-4 approved about $5–10 of GPU time. The spend exceeded that, for three reasons:
- the first pod used up the account's starting balance on phases 1–2 and then on the lost phase 3–4
  attempt (run note 3);
- the second pod used about $10, most of it sitting idle after phase 3 (run note 4);
- scoring cost $0.22.

The overrun bought no extra data and changed nothing in the design.

## Deviations

**CD-1 — model snapshots recorded from the download cache, not the run manifest.** Plan section 2 says the
manifest records each endpoint's served snapshot through `/v1/models`. The servers require an API key,
and the manifest's query sent none, so that field is empty. The snapshots were instead read from the
pod's Hugging Face cache after collection (`confirm_data/model_snapshots.json`). Each model had exactly
one snapshot, so this identifies what was served.

| model | snapshot |
|---|---|
| Qwen/Qwen3-8B | `b968826d…` |
| huihui-ai/Huihui-Qwen3-8B-abliterated-v2 | `7d89db76…` |
| yukiyounai/Jailbreak-R1 | `d095f88d…`, the same as E1 |
| Qwen/Qwen2.5-7B-Instruct | `a09a3545…`, the same as E1 |
| NousResearch/Meta-Llama-3.1-8B-Instruct | `d10aef79…`, the same as E1 |

The vLLM version was recorded correctly through `/version`. This deviation has no effect on the data.
