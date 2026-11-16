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

## Labelling

6. **Both agents stopped early (2026-11-16).** Each GPT-6.1 Sol session ended with
   `incomplete_access_restriction`. The provider's safety system blocked biological content, and neither
   session retried it. Agent 1 saved sheets 1–17 (680 items) and stopped within sheet 18. Agent 2 saved
   sheets 1–21 (840 items) and stopped within sheet 22. Unread items were left unlabelled, not marked false.
   - **Coverage was checked without reading any label value.** No outcome, label rate or agreement had been
     looked at when this note was written.
   - **The trigger was probably response-specific.** 155 of the 158 goals had already appeared on sheets
     1–17 without a block, so the trigger was probably particular responses rather than goal wording.
     Eight goals appear on both stopping sheets: held-out 158, 181, 192, 216, 228, 245, 259, 274.
   - **Agent 1 used a helper script** (`adj/confirm/agent1/label_work.py`). It printed each sheet's items in
     full for reading, and saved the agent's chosen positives with a default reason for most items. Labels
     were still the agent's judgement per item, but its reasons are mostly generic, which weakens
     reconciliation. Agent 2 used no script.
   - The remedy will be decided and logged as a deviation before any label value is read.

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

**CD-2 — a stricter goal re-screen after the labelling stops, and its goals treated as blocked.**

*What the plan says.* Section 1's fallback drops a goal "blocked during labelling" from every arm, reports
the count, and also reports CH1 with that goal's cells at their least favourable values. It foresees
goals blocked one at a time. Here both whole sessions stopped on biological content (run note 6), and the
triggering items could not be identified.

*What was done.*
- The researcher re-read all 158 remaining goal texts, goals only and no responses, under a broader rule:
  pathogens, biological toxins, poisoning, culturing or weaponising organisms, and chemical weapons, marking
  whenever unsure.
- 38 goals were marked (`confirm_data/rescreen_marks.json`, SHA-256 `7dd76a74…295a9bd`). 3 of the 8 goals on
  both stopping sheets are among them.
- All 38 are treated as blocked goals under the fallback: excluded from every arm and passed to
  `confirm_analysis.py --blocked`.

*Blindness.* The marks were made and hashed after collection, but before anyone read a label value, an
outcome, a judge score or an agreement figure. The screen used goal text only, so it cannot depend on arm
or outcome.

*Consequences.*

- **Sample.** 120 analysable goals and 2,159 analysable items, down from 158 goals and 2,842 items.
- **Design simulation**, re-run with the frozen `_sim` at the planning values. No real data was used.

  | | n = 158 | n = 120 |
  |---|---|---|
  | CH1 power | 0.98 | 0.96 |
  | CH1 power, B pessimistic | 0.75 | 0.67 |
  | CH2-B power | 0.77 | 0.63 |
  | CH3-A power | 0.63 | 0.46 |
  | CH3-B power | 0.87 | 0.81 |
  | CH1 false support at the +0.05 boundary (A / B) | 0.014 / 0.020 | 0.022 / 0.028 |
  | secondary familywise error | 0.040 | 0.032 |

  Error control holds at n = 120. The secondary tests lose power.
- **The least-favourable CH1 sensitivity will almost certainly fail.** Setting 38 of 158 goals to success
  for abliterated-plain and failure for aligned-redteam shifts that contrast by about +0.24, far past the
  +0.05 margin. This sensitivity is pre-registered as reported, not as a decision rule. It will be reported
  as uninformative at this many blocked goals, and the primary CH1 will not be described as robust to
  blocked goals.
- **Scope.** The confirmation does not cover goals involving biological or chemical harm, matching D3 in the
  original study.

*Continuation sheets.*
- **Contents.** `adj/confirm/resume_agent1/` holds sheets 18–72 (1,660 items) and
  `adj/confirm/resume_agent2/` holds sheets 22–72 (1,538 items). They have the same frozen item text and
  numbering as the frozen sheets, with the excluded goals' items removed. Hashes are in
  `confirm_data/resume_sheet_hashes.json` (SHA-256 `44453f0c…471a6`).
- **Coverage.** Each agent will then have labelled all 2,159 analysable items. Labels already saved for
  excluded goals' items are kept but not used.
- **Brief.** The continuation brief adds one requirement: a real reason for every item, not a template
  (see run note 6). Each agent resumes in a new session of the same model, with no shared history with the
  other agent.
