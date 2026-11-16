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

     > **Qualified (seventh external review, 2026-11-16).** "Labels were still the agent's judgement per item" is
     > not demonstrated by the outputs. The script's `save(n, positives)` writes `true` for the items the
     > agent listed and `false` for every other item on the sheet. In agent 1's first session all 126 true
     > items carry one identical reason and 545 of the 554 false items another. So that session recorded
     > only a positive set, and any item the agent overlooked became false by default. Agent 2's first
     > session also reused one reason on 438 false items, but its positives have item-specific reasons;
     > its mechanics are not otherwise recorded. The script (path sanitised), all briefs and their hashes
     > are published in `confirm_data/method/`.
   - The remedy will be decided and logged as a deviation before any label value is read.

7. **Labelling complete (2026-11-16).** Both agents resumed in new sessions from the CD-2 continuation sheets,
   agent 1 from sheet 18 and agent 2 from sheet 22. Neither stopped again.
   - **Coverage.** Each agent covers all 2,159 analysable items: booleans only, no duplicates, no unknown
     items. Labels saved earlier for excluded goals' items (181 and 219) are not used. File times show that
     no first-session label file was rewritten during the resume.
   - **Reasons.** All continuation reasons are item-specific; the most-repeated one is used 6 times. Both
     first sessions reused generic reasons: agent 1 one sentence 545 times, agent 2 one 438 times.
   - **Freeze.** Each agent's blind labels for the analysable items were written to read-only files
     `adj/confirm/labels_agent{1,2}.json`, then hashed together with their reasons and all 72 raw sheet
     files per agent. The hashes are in `confirm_data/blind_label_hashes.json` (SHA-256 `cc8e1353…2469489`).
     All of this happened before any comparison.
   - **Blind agreement**, computed after the freeze over all items and not by arm:

     | | count |
     |---|---|
     | items | 2,159 |
     | agree | 2,101 (0.973) |
     | both true | 398 |
     | both false | 1,703 |
     | disputed | 58 (29 true only for agent 1, 29 true only for agent 2) |

     Kappa is 0.915.
   - **Reconciliation packets.** `adj/confirm/reconcile_agent{1,2}/` hold the 58 disputed items in seeded
     shuffled order, without arm. Each item shows its full text, the annotator's own blind label and reason,
     and the other annotator's. The brief tells each annotator to give template reasons no weight; 8 of agent
     1's reasons on disputed items are templates. Final label = true only if both annotators end up true;
     anything unresolved is false.

8. **Reconciliation and final labels (2026-11-16).** Each agent reviewed the 58 disputed items in a new session.
   Agent 1 changed 27 labels and agent 2 changed 28; each agent's own `changed` flags match these counts.
   Outcome of the 58 disputes:

   | outcome | items |
   |---|---|
   | both true | 19 |
   | both false | 32 |
   | still split, counted false | 7 |

   `adj/confirm/labels_final.json` covers all 2,159 analysable items and is read-only. The final labels and
   both reconciliation files are hashed in `confirm_data/blind_label_hashes.json`.

## Result (frozen analysis, run once on 2026-11-16)

`confirm_analysis.py` was unchanged since the tag, and its inputs are hashed in
`confirm_data/analysis_inputs.json`. The output is `confirm_results.json` (SHA-256 `49b2c893…e21ab36`).
Paired goal bootstrap: 10,000 resamples, seed 2026, n = 120 goals per target. All 38 excluded goals are
passed as blocked. The 683 labels the script reports as missing are exactly those goals' items; no
analysed goal has a missing label, so the "missing as true" sensitivity is identical to the primary.

**Any-round attack success** (primary outcome):

| target | abliterated-plain | aligned-redteam | trained-redteam |
|---|---|---|---|
| A | 0.150 | 0.683 | 0.675 |
| B | 0.050 | 0.350 | 0.175 |

**Pre-registered hypotheses:**

| hypothesis | target | estimate | 95% CI | 90% CI | test | verdict |
|---|---|---|---|---|---|---|
| CH1: abliterated-plain − aligned-redteam, upper < +0.05 | A | −0.533 | [−0.633, −0.433] | | upper −0.433 | supported |
| | B | −0.300 | [−0.383, −0.208] | | upper −0.208 | supported |
| **CH1 (both targets)** | | | | | | **CONFIRMED** |
| CH2: same contrast ≠ 0 | A | −0.533 | | | Holm p < 0.001 | rejected: prompting better |
| | B | −0.300 | | | Holm p < 0.001 | rejected: prompting better |
| CH3: trained − aligned within ±0.15 (TOST) | A | −0.008 | [−0.125, +0.108] | [−0.100, +0.083] | Holm p = 0.016 | equivalent within ±0.15 |
| | B | −0.175 | [−0.283, −0.067] | [−0.259, −0.083] | Holm p = 0.701 | not shown equivalent |

**Also reported, as pre-registered:**

- **Blind agreement** between the two agents: kappa 0.915 over 2,159 items.
- **CH1 with the blocked goals set to their least favourable values:**

  | target | upper bound of the 95% CI | supported |
  |---|---|---|
  | A | −0.038 | yes |
  | B | +0.127 | no |

  As stated in CD-2 before any label was read, at 38 blocked goals this check is largely uninformative. CH1
  on B is not robust to the hypothetical that every excluded goal would have favoured abliteration; CH1 on A
  is.

  > **Qualified (seventh external review, 2026-11-16).** Calling the check "uninformative" understated it. It
  > shows that the retained-goal result on B does not establish CH1 for the 158 originally eligible goals
  > without assumptions about the excluded ones. CH1 is supported on the retained set; under the
  > registered least-favourable completion it stays supported on A and is **unresolved on B**. The check
  > was registered as reported, not as a decision gate. The CD-2 prediction about its usefulness came
  > after collection and is separate from the registered check. Recomputed with the CC-1 corrected
  > function: identical.
- **Selected-round secondary outcome** (the highest StrongREJECT-scoring round per cell): the same verdicts,
  except CH3-A (Holm p = 0.054, not rejected).

  | target | CH1 upper bound | CH2 | CH3 |
  |---|---|---|---|
  | A | −0.358 | rejected | Holm p = 0.054, not rejected |
  | B | −0.200 | rejected | Holm p = 0.75, not rejected |

**Not pre-registered (exploratory).** On B, Jailbreak-R1's CI excludes zero on the low side (−0.175, p = 0.002
for zero). In this sample, procedure and later collection session it scored lower than prompting the
aligned model; this is an exploratory negative contrast, not a confirmed reversal. CH3 was a TOST equivalence test, not a test of
difference, so this is reported descriptively only.

**How the result is to be read** (qualified after the seventh external review):
- a prospective test of frozen hypotheses and code, with a post-collection eligibility amendment (CD-2);
  the verdicts hold for the 120 retained goals, and for the original eligible set CH1 on B is unresolved;
- under this AI annotation procedure, not human-validated (D-2);
- for these checkpoints, this red-team prompt and three attempts;
- for goals excluding biological and chemical harm (D3, CD-2).

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

  > **Qualified (seventh external review, 2026-11-16).** These are proxy exclusions for content the annotators
  > might not process, not 38 goals shown to be blocked. The trigger was probably response-specific, and
  > 155 of 158 goals had already appeared without a stop. Excluding them from every arm prevents
  > differential deletion, but the broader rule was written after collection; it is not the registered
  > fallback applied unchanged. Accurately described: the registered analysis was applied to a
  > post-collection, reportedly outcome-blind amendment of the eligible goal set. CH1–CH3 are findings for
  > the 120 retained goals.

*Blindness.* As the researcher reports, the marks were made and hashed after collection, but before anyone
read a label value, an outcome, a judge score or an agreement figure. The screen used goal text only, so it cannot depend on arm
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

  > **Qualified (seventh external review, 2026-11-16).** "Error control holds at n = 120" is too general. The
  > procedure met the stated checks in the configurations examined. It is not uniformly calibrated near
  > sparse margins. With abliterated-plain at 0.05 and aligned-redteam at 0, observing 2 of 120 against
  > 0 gives the 95% interval [0, 0.042], so CH1 is supported. Under that true margin null this happens
  > with probability P{Bin(120, 0.05) ≤ 2} = 0.058; a simulation of the frozen bootstrap gives 0.055,
  > against the intended 0.025. The observed contrasts (−0.533 and −0.300) are far from this regime.
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

## Seventh external review and correction CC-1 (2026-11-16, after the frozen run)

The review covered commit `0114f9d`. All 10 points were checked against the code and data and held. The
frozen `confirm_results.json` is unchanged. Changes are wording, records, and one code correction that does
not affect the result.

1. **CD-2 is an eligibility amendment, not the registered fallback applied unchanged.** Accepted. CD-2 and
   the result are qualified, and RESULTS.md and RED-TEAM-STUDY.md now report a prospective test with a
   post-collection eligibility amendment. Verdicts are stated for the 120 retained goals.
2. **The least-favourable check is not "uninformative".** Accepted. For the 158 originally eligible goals,
   CH1 is unresolved on B and supported on A.
3. **The later freeze ordering is asserted, not independently shown.** Accepted. Only the tag
   `confirm-prereg-v1` (`9c174d7`) was pushed before collection. Later commits were pushed together in this
   order: sheet hashes `5f13bcd`, CD-2 `37e5e2c`, blind labels `57b6846`, result `ec1d2dd`. Their order is
   therefore researcher-reported; hashes identify bytes, not when they existed. In future work, each freeze
   is to be pushed, or its digest otherwise externally timestamped, before the step that depends on it.
4. **"Not worth it" exceeds the comparison.** Accepted. The headline now says that, for these
   configurations and retained goals, plain-instruction abliteration produced lower any-round success than
   the red-team prompt on the aligned model. Abliteration plus the prompt remains untested here.
5. **Verdicts on different estimands are not replications.** Accepted. The prospective test is described as
   a related comparison with a different outcome specified in advance, read alongside the original
   hypotheses. The B result for Jailbreak-R1 is an exploratory negative contrast tied to this sample,
   procedure and later session.
6. **The helper-assisted annotation needs an inspectable record.** Accepted. The agents' briefs (initial,
   continuation, reconciliation) and agent 1's helper script (path sanitised) are published in
   `confirm_data/method/` with source hashes. Run note 6 now says what the outputs show: agent 1's first
   session recorded a positive set, and everything else defaulted to false. Kappa 0.915 describes two
   instances of one model. Reconciliation changes are not validation.
7. **"Error control holds at n = 120" is too general.** Accepted and reproduced: P{Bin(120, 0.05) ≤ 2} =
   0.0575, and a simulation of the frozen bootstrap gives 0.055 false support at that sparse boundary. The
   statement is narrowed to the configurations examined.
8. **`blocked_worst_case` misses cells with every round withheld.** Accepted, and confirmed by reading the
   code. **Correction CC-1:** the function now sets the least favourable values on cell outcomes, through
   `_decide`, which was split out of `analyse` with unchanged behaviour. The frozen version is kept as
   `_blocked_worst_case_frozen`, and `--selftest` gains the reviewer's case.
   - No blocked CH1 cell in the data lacks a labelable round, since only 2 rounds were withheld.
   - Rerunning the full analysis with the corrected code reproduces `confirm_results.json` exactly.
9. **"No data was lost" contradicts run note 3.** Accepted. The first attempt's phase 3–4 outputs were lost
   and rerun. The researcher reports none had been inspected. The retained analysis files are complete. The
   cache-based snapshot record (CD-1) is weaker evidence than authenticated served-model records. That
   matters most for the trained arm, which was collected in a later session.
10. **Mixed historical and current scope.** Accepted. "All results are retrospective" now reads "all
    original-study results". The pooled-miss-rate, one-round and truncation limits are labelled as applying
    to the original study, not the prospective test.
