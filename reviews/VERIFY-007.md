# VERIFY-007: independent verification of REPAIR-007 (whole-project audit before submission)

Verifier, cycle 7. Scope: the uncommitted repairs on top of `41f724a` (`README.md`,
`paper/CAPSTONE-PAPER.md`, `paper/make_figures.py`, `reviews/check_freeze_delta.py`,
`stage_d/DEVIATIONS-AND-LIMITATIONS.md`, `stage_f/F-EXECUTION-NOTES.md`) and the git-ignored
`stage_c/ctf_trial_results.json` that R7-01 proposes to release, checked against REVIEW-007. I read every
changed hunk and re-derived the numbers from the results files rather than relying on REPAIR-007.

Rules followed: no cloud, pod, key or spend; no push, commit or `git add`; `~/.runpod` untouched. The
label-sheet folder was not opened: R7-03 was checked from `make_label_sheet.py` and `f2_summary.json`
only. No model output text was read. Scratch scripts and the clean-copy figure run lived in the session
scratchpad. In the repository I wrote this file and made the three small fixes listed at the end.

## What I ran

| Check | Result |
|---|---|
| `freeze_f.py check` (WSL, root) | **"stage F freeze verifies"** |
| `freeze_v2.py check` (WSL, root) | **"CTF v2 freeze verifies"** |
| `stage_f/test_f.py` (WSL, `python3 -B -m unittest`) | 23 tests, OK |
| `reviews/check_freeze_delta.py` (WSL, root, stage D venv) | passes: modified `EXPANDED-STUDY-PLAN.md`, `score_run1.py`, `test_run1.py` (repaired 2, appended 1); added the 3 documented stage D documents; all other frozen hashes match |
| Mutation test of `check_freeze_delta.py` (scratchpad script, monkeypatched `working()`) | prepending one byte to `score_run1.py`, `test_run1.py` or `EXPANDED-STUDY-PLAN.md` each makes the script fail with the right message, so it does not pass trivially |
| Clean copy: `git archive HEAD` + `stage_c/ctf_trial_results.json` + working `make_figures.py`, with `paper/figures/*` deleted first | `paired_ci.py` and `make_figures.py` exit 0; `paired_ci.json` and all six SVGs **byte-identical** (`cmp`) to the working tree |
| Cited-file check (every backticked path in paper and README that exists) | all tracked except `stage_c/ctf_trial_results.json` (to be force-added) and `reviews/REPAIR-007.md` (new this cycle) |
| Privacy grep (`rpa_`, `csawctf{`, `flag{`, Windows/WSL user paths) over all changed files, REVIEW/REPAIR-007 and `ctf_trial_results.json` | no hits other than the two review files naming the patterns |
| Figure citations | Figures 1 to 6 each cited in the body (Figures 3 and 4 now twice, counting captions) |

## Verification table

| Finding | Verdict | Evidence | Remaining |
|---|---|---|---|
| **R7-01** (minor) figure script needs an ignored file | **VERIFIED** (pending the builder's `git add -f`) | `git check-ignore` confirms `.gitignore:12 *_results.json`. I parsed all 28 records myself: the 20 keys are `task_id`, `condition`, `phase`, `status`, `solved`, `reason`, `final_text_class`, integer counts, timings, `checkpoint`, `revision`. Every string value is one of 14 task ids, `control`/`main`, four phase names, two statuses, five ending reasons, `empty`, the two public model ids and two revision hashes. No flag-like string, credential, model text or personal path. Figures regenerate byte-identically from HEAD plus this file. §11 and Appendix B are then correct as written. | builder must run `git add -f stage_c/ctf_trial_results.json` |
| **R7-02** (minor) freeze-delta script failed; undisclosed post-freeze plan append | **VERIFIED** | `git show 418edc1`: 2026-11-19 17:40:13 −05:00, after the run 1 freeze (`ba2d5bd`, 14:37) and after VERIFY-001 (`97f850f`, 17:19); it appends 9 lines ("Decision update") cancelling the B–D follow-up and making run 2 = CTF v2, as D-31 says. `git diff 418edc1 -- EXPANDED-STUDY-PLAN.md` and `git diff 97f850f HEAD -- score_run1.py test_run1.py` are empty. The new script logic is sound: all non-target frozen hashes must still match, the modified set must equal exactly the three names, each repaired file's `97f850f^` blob must match its frozen hash and the working file must equal its `97f850f` blob, and the plan's `418edc1^` blob must match its frozen hash with the working file starting with it. The mutation test shows each check bites. The deviations-file sentence at l.18–23 and D-31 are accurate. No freeze manifest contains `check_freeze_delta.py`. | none |
| **R7-03** (minor) `ended_by` column partially unblinds | **VERIFIED** | `make_label_sheet.py:91`: `ended_by` is `solved` if `status == 'solved'`, else `row['reason']`. `f2_summary.json` `descriptive.ending_reasons`: aligned `agent_ended_without_verified_flag` 10, `verified_flag` 4; abliterated `verified_flag` 14; Heretic `verified_flag` 11, `time_cap` 2, `submission_budget` 1. Solved counts 4/14/11 equal the `verified_flag` counts, so `solved` appears in all arms and only 10 + 3 = **13 of 42** rows reveal the arm. Aligned refused = 10 = its text-reply endings (`analyze_f.py:259` scores refusal from that reason), so the column is a proxy for the rule outcome. Paper §7.3, §9 and the notes state this consistently. | none (I re-indented the §9 continuation lines; see fixes) |
| **R7-04** (minor) 2-in-flight speed-up | **VERIFIED** | `posthoc_v2.json` `decode_tok_per_s_by_trials_in_flight`: 1 vs 3 in flight 41.14/35.81, 40.7/36.21, 41.9/35.1 = +14.9/+12.4/+19.4%; 2 vs 3 40.24/35.81, 37.41/36.21, 39.2/35.1 = +12.4/+3.3/+11.7%. Heretic unlimited_subway `min_in_flight` 2, so "about 12%" and "never ran with only one in flight" are right. §9 "up to 12–19%" is right. | none |
| **R7-05** (minor) §3.3 stale | **VERIFIED** | scoped to "capability or attack success (stage B and v2)"; adds the stage F sentence pointing to Section 7. Consistent with abstract, §8 and §13. | none |
| **R7-06** (minor) empty-answer qualifier | **VERIFIED** | `f1_summary.json` `full_refusal_excl_capped_or_no_answer`: 0 vs 51 over 74 pairs (abliterated), 0 vs 74 over 111 pairs (Heretic). §8.1 and §13 now carry the qualifier. | none |
| **R7-07** (minor) README stale | **VERIFIED** | New top block: 9/8/8 of 14 and McNemar p = 1.0 (`ctf_v2_summary.json`), 1,200 s / 50 calls (`V2-PROTOCOL.md` l.50–51), $9.87 (`CTF-V2-RESULTS.md` l.287); F1 181/0/0 with the empty-answer caveat; F2 10/0/0 refused and 4/14/11 solved (`f2_summary.json`); $5.47 (`F-EXECUTION-NOTES.md` l.85, $5.465). The stage C entry is marked superseded; "8 of the 14 … omitted the target address" matches D-26. All link targets exist. | fixed a lowercase sentence start ("the recent" → "The recent") |
| **R7-08** (nit) | **VERIFIED** | `posthoc_v2.json` contiguous 9/8/7 matches "(in one Heretic trial split across two `xxd` lines)". | none |
| **R7-09** (nit) | **VERIFIED** | Table 10 now "revisions in `v2_config.json`". | none |
| **R7-10** (nit) | **VERIFIED** | "(Figure 3)" after the §5.2 interval sentence (Figure 3 is the paired-CI plot); "; Figure 4" after the endings sentence in §5.3 (Figure 4 is the endings plot). | none |
| **R7-11** (nit) | **VERIFIED** | §1.2 item 4 says "from the fixed text". | none |
| **R7-12** (nit) | **VERIFIED** | "Endings" bullet moved unchanged to the top of "Descriptive details". | none |
| **R7-13** (nit) | **VERIFIED** | header sentence added; accurate. | none |
| **R7-14** (nit) | **VERIFIED** | matches `f1_summary.json` `"Wilcoxon signed-rank (normal approx.)"`. | none |
| **R7-15** (nit) | **VERIFIED** | message now "for figure 3"; `paired_ci.json` feeds `fig3_paired_ci.svg`. | none |
| **R7-16** (nit) | **VERIFIED** | §9 wording now matches the notes ("root-only inside WSL"). | none |
| **R7-17** (nit, process) | **VERIFIED** after my edit | header says cycle 7; Appendix D cycle 7 row counts (17; 0 major, 7 minor, 10 nit) are right. I updated the outcome cell to cite this file and to include the stage F notes among the edited files. | none |

## New issues found

None that change a number. Two cosmetic issues introduced by the repair, both fixed below.

## Fixes applied by the verifier

1. `README.md`: "not comparable with v2. the recent uncensored model" → "… v2. The recent uncensored model".
2. `paper/CAPSTONE-PAPER.md` §9 "F2 refusal is a rule" bullet: indented the three continuation lines added
   by the repair to match the list's other bullets (rendering unchanged; source consistency).
3. `paper/CAPSTONE-PAPER.md` Appendix D cycle 7 outcome cell: now "all 17 verified (`reviews/VERIFY-007.md`):
   16 fixed in this paper, the README, the deviations file, the stage F notes and two scripts; R7-01
   resolved by releasing `stage_c/ctf_trial_results.json` (counts and reasons only) with this cycle's
   commit".

No frozen file was edited (both freezes still verify after the fixes; neither manifest covers the README,
the paper, the deviations file, the stage F notes or `reviews/`).

## Summary

17 of 17 findings **verified** (0 partly fixed, 0 not fixed); 0 new substantive issues; 3 small verifier
fixes. The tree is ready to commit once the builder force-adds `stage_c/ctf_trial_results.json` and adds
`reviews/REVIEW-007.md`, `reviews/REPAIR-007.md` and `reviews/VERIFY-007.md`.
