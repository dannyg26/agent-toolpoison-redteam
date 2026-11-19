# REPAIR-001: repairs and disclosures for REVIEW-001

**Date:** 2026-11-19. **Role:** repairer. **Branch / HEAD:** `stage-c-ctf-prefreeze` @ `ba2d5bd`. Nothing was
committed, pushed, reset or checked out.

**Limits I kept to.** I made no cloud or RunPod call, no ssh, no launch and no paid action. I read no key
file and no model output text: stage D and stage C facts come from logs, label files and aggregate
counts or lengths only. I did not change study scope or `EXPANDED-STUDY-PLAN.md`. All files written have
LF line endings (checked: no `\r` in any changed file).

**Frozen artefacts changed.** Only `stage_d/score_run1.py` and `stage_d/test_run1.py`, as a pre-scoring bug
fix and guard (D-01, D-02). `RUN1-PROTOCOL.md` was restored to its frozen bytes. `run1_freeze.json` was
**not** regenerated.

**Freeze status after repair.**
- Immediately after restoring the protocol, before any other edit, `freeze_run1.py check` printed
  `run 1 freeze verifies`.
- It now fails by design. It lists `score_run1.py`, `test_run1.py` and the three new unfrozen stage D
  documents, because `freeze_run1.sources()` hashes every `.md`, `.py`, `.sh` and `.json` file in `stage_d/`.
- `reviews/check_freeze_delta.py` verifies that the difference is exactly that and that every other
  frozen hash matches. It also checks that the committed versions of the two edited files equal their
  frozen hashes.
- Consequence: `launch_run1.py --launch` will refuse to run against `run1_freeze.json`. A follow-up needs
  its own `run1c_freeze.json` (see `stage_d/FOLLOWUP-DESIGN.md`, item 13).

## Verification commands (Git Bash; WSL paths)

```
# V1  unit tests (27 tests, all must pass; InjecAgentFidelity must say "ok", not "skipped")
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash -c 'cd /mnt/c/Users/danny/Downloads/agent-toolpoison-redteam/stage_d && /home/capstone-study/stage_d/venv/bin/python -m unittest -v test_run1 test_launch_run1'
# V2  frozen-scope delta is exactly the documented one
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash -c 'cd /mnt/c/Users/danny/Downloads/agent-toolpoison-redteam && /home/capstone-study/stage_d/venv/bin/python reviews/check_freeze_delta.py'
# V3  protocol restored byte-for-byte (no output = identical)
cd /c/Users/danny/Downloads/agent-toolpoison-redteam && git diff --stat HEAD -- stage_d/RUN1-PROTOCOL.md && sha256sum stage_d/RUN1-PROTOCOL.md   # ffac16fd...4c64
# V4  real scoring completes
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash -c 'cd /mnt/c/Users/danny/Downloads/agent-toolpoison-redteam/stage_d && /home/capstone-study/stage_d/venv/bin/python score_run1.py /home/capstone-study/stage_d/sessions/run1b > /home/capstone-study/stage_d/sessions/run1b/summary.json; echo EXIT=$?'
# V5  pod time
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- cat /home/capstone-study/stage_d/launch/run1b/run_status.json   # deadline_epoch 1795127890.405 - 10800 s = 19:38:10.4 UTC
cd /c/Users/danny/Downloads/agent-toolpoison-redteam && git log -1 --format=%cd --date=iso ba2d5bd && git reflog show --date=iso origin/stage-c-ctf-prefreeze | head -1
# V6  the regression test fails against the frozen scorer: put `git show HEAD:stage_d/score_run1.py` in a
#     temporary module and run MissingArms.test_aligned_only_session_scores against it -> KeyError: 'abliterated'
#     (done during repair; the temporary file was removed)
```

**Real scoring result (V4).** Exit 0, `score.err` empty, and `summary.json` is 12,519 bytes.
- Top-level keys: `arms`, `unobserved_arms`, `B`, `C`, `D`, `diagnostics`.
- `arms: ["aligned"]`; `unobserved_arms: ["abliterated", "heretic"]`.
- All 27 paired rows (B and C) are `available: false`.
- Diagnostics: aligned requests 5,146, unclosed thinking 1,490, hit max tokens 1,593.
- `scored_rows.jsonl` was rewritten (5,146 rows), and the CWEval container runs executed.

## Findings table

Line numbers refer to the working tree after repair.

| ID | Action | Files and lines changed | How to verify | Notes |
|---|---|---|---|---|
| R1-01 | **fixed** (pre-scoring bug) | `stage_d/score_run1.py` 129–172 (`paired`, `with_holm`), 273 (`unobserved_arms`); `stage_d/test_run1.py` 184–263 (`write_session`, class `MissingArms`), 180–181 (two extra asserts in the E2E test) | V1, V4, V6; `DEVIATIONS-AND-LIMITATIONS.md` D-01 | Holm family fixed at m = 2. With both primary arms present it is the frozen Holm (unchanged). Otherwise `p_holm_primary` is `null`, with `holm_status` set, and each available primary row gets `p_primary_bound_m2 = min(1, 2p)` (Bonferroni, an upper bound on the final Holm value; tested). Unavailable contrasts are reported with `available: false`. |
| R1-02 | disclosed (operational; events already happened) | `stage_d/RUN1-EXECUTION-LOG.md` (timeline, entries 2–3 and correction); `DEVIATIONS-AND-LIMITATIONS.md` D-03, D-04 | `progress.log` / `run_status.json` timeline (V5) | Abliterated was stopped and the judge ran on aligned only. Entry 2's "judge on aligned and abliterated" is marked superseded. Abliterated is unobserved; no fallback retry occurred. |
| R1-03 | **fixed** | `stage_d/RUN1-PROTOCOL.md` restored to `git show HEAD:` bytes; entries 2–3 moved to the new `stage_d/RUN1-EXECUTION-LOG.md` (entries 2–3, lines 36–53) | V3; `freeze_run1.py check` passed right after the restore (before other edits); V2 now | `run1_freeze.json` not regenerated. A follow-up freeze is designed in `FOLLOWUP-DESIGN.md` item 13, not created. |
| R1-04 | disclosed | `DEVIATIONS-AND-LIMITATIONS.md` D-07 (lines 117–125); execution log entry 4 | `summary.json` diagnostics | Run 1 aligned: 1,490/5,146 unclosed, 1,593 `length`. Per-source rates and the closed-reasoning sensitivity analysis are left for the analysis write-up (not implemented: they are post hoc additions, not scoring fixes). |
| R1-05 | disclosed | D-08 (lines 127–133) | `pod_judge.py` and `judge.log` "376 of 813" | Four-class counts are already in `summary.json` (`willingness_counts`). |
| R1-06 | disclosed | D-09 (lines 135–142) | `aligned.log.json`: `step2_requests` 0, `step2_unobserved` 0 | Aligned had 0 step-1 data-stealing successes, so the cache was never consulted in run 1. The issue matters for the follow-up arms. |
| R1-07 | deferred to follow-up (and disclosed) | `FOLLOWUP-DESIGN.md` items 7 and 9; D-06 | read the files | Anchor subset and single-pass re-judging are designed only. |
| R1-08 | disclosed and deferred | D-10; `FOLLOWUP-DESIGN.md` item 2 | `install.log` has no versions | Run1b transitive versions and judge revisions are unrecoverable from the downloaded files. |
| R1-09 | disclosed; check deferred | D-11; `FOLLOWUP-DESIGN.md` item 14 | WSL search found no local copy of the arms' tokenizer or config files | **Not done:** comparing the files needs a Hub download, which needs explicit permission. Disclosure wording is provided for the meantime. |
| R1-10 | **fixed** (wording) and disclosed | `stage_c/CTF-RESULTS.md` 125–132 (new bullet), 134–141 (post-review corrections note); `README.md` 11–13; D-23 | Recompute from `stage_c/ctf_trial_results.json`: median of `generation_seconds_total/elapsed_seconds` = 0.792 (28 trials, range 0.352–0.957); time-limit trials 0.792 (0.574–0.938) | Per-arm generated tokens and tool calls added (main 65,269 / 178; control 64,817 / 189). |
| R1-11 | **fixed** (wording) | `stage_c/CTF-RESULTS.md` 18–26 (headline paragraph), 60 (table row), 79–82 (thinking-budget bullet); `README.md` 7–9; D-22 | Private traces: the final `model_response` of the 3 `agent_ended_without_verified_flag` trials has `finish_reason: "length"`, `completion_tokens` 4096 = `reasoning_tokens` 4096, content null | This confirms the reviewer's hypothesis: the endings were truncations. Measured reasoning tokens >1,024: 14/111 main and 14/115 control responses, max 4,096. The frozen chars/4 estimate (12 per arm, ≈3,100) is kept and labelled as an estimate. |
| R1-12 | **fixed** | `RUN1-EXECUTION-LOG.md` timeline (lines 10–30) and entry 2 (lines 36–44) | V5 | `createdAt` = 19:38:10.4 UTC (guard deadline 22:38:10.4 minus 180 min). The commit was at 19:37:11 UTC and the push at 19:37:55 UTC (reflog of the remote-tracking ref), so the pod was created about 15 s after the push. Terminated after 135.41 min (≈21:53:35 UTC); quoted $5.005. |
| R1-13 | disclosed and deferred | D-04; `FOLLOWUP-DESIGN.md` item 8 | `aligned.log.json`: `tokenizer_from_base: false`; `progress.log` has no "retry" line | No retry happened in run1b. The `.loaded` marker is designed only. |
| R1-14 | **fixed** (pre-scoring guard; no rule change) | `stage_d/score_run1.py` 185–218 (`load_generation`, `check_items`), 231–233 (`score`); `test_run1.py` 168 (`.done` in E2E test), 252–263 (3 guard tests) | V1, V4; D-02 | An arm needs both `.jsonl` and `.done`. Duplicates or incomplete step-1 coverage raise an error. Item hashes are checked against `run1_freeze.json`. No effect on run1b. |
| R1-15 | disclosed | D-12 | — | "Any refusal" companion and per-arm confusion matrix are recommended for the write-up. |
| R1-16 | disclosed; (c) deferred | D-13; `FOLLOWUP-DESIGN.md` item 14 | — | The extraction-diagnostic count was not implemented (post hoc analysis, needs output content). |
| R1-17 | disclosed | D-14 | — | Paired CIs not implemented (descriptive addition for the analysis stage; no contrasts exist yet). |
| R1-18 | disclosed | D-16 | — | — |
| R1-19 | disclosed; deferred | D-15; `FOLLOWUP-DESIGN.md` item 14 | — | **Not done:** `sample_validation.py` is a new study instrument. Its design (stratification, blinding, rater-wellbeing plan) is the author's decision, and it must be committed before any output is opened. |
| R1-20 | **fixed** (evidence recorded) | `RUN1-EXECUTION-LOG.md` entry 4 (lines 54–73); D-17 | V1 output line `test_same_verdicts (test_run1.InjecAgentFidelity...) ... ok` | Adding realistic formats to the differential set is deferred (frozen test; follow-up). |
| R1-21 | disclosed and deferred | D-21; `FOLLOWUP-DESIGN.md` items 6 and 12 | `aligned.log.json` `step1_seconds` 7382.64 | 123.0 min vs the plan's 45 min per model for B–D. |
| R1-22 | disclosed | D-18 | — | — |
| R1-23 | disclosed and deferred | execution log entry 4; D-19; `FOLLOWUP-DESIGN.md` item 10 | — | "Removed only the index folder" is recorded as observed by the operator during the run; I could not verify it independently, because the pod is gone. |
| R1-24 | disclosed | D-25 | — | For the run 2 protocol, which does not exist yet. |
| R1-25 | **fixed** | `README.md` 7–16 (stage C paragraph; lines 3–6 unchanged) | read `README.md` lines 3–16 | Now mentions the two failed setup leases and the manual install re-run, rewords the refusal clause and adds the generation share. |
| R1-26 | disclosed | D-20 | — | — |
| R1-27 | deferred to follow-up | `FOLLOWUP-DESIGN.md` item 11 | — | Launcher not modified (`launch_run1.py` is frozen). |

## Files changed or added

- Modified (frozen, pre-scoring fix): `stage_d/score_run1.py`, `stage_d/test_run1.py`
- Restored to frozen bytes: `stage_d/RUN1-PROTOCOL.md` (now identical to HEAD)
- Modified (non-frozen wording): `stage_c/CTF-RESULTS.md`, `README.md`
- Added: `stage_d/RUN1-EXECUTION-LOG.md`, `stage_d/DEVIATIONS-AND-LIMITATIONS.md`,
  `stage_d/FOLLOWUP-DESIGN.md`, `reviews/check_freeze_delta.py`, `reviews/REPAIR-001.md`
- Private (WSL) outputs regenerated by V4: `/home/capstone-study/stage_d/sessions/run1b/summary.json`,
  `scored_rows.jsonl`, `score.err` (now empty)

The untracked `stage_e/` directory in the working tree was not created or touched by this repair.
