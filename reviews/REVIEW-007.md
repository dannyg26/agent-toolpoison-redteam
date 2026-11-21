# REVIEW-007: whole-project correctness audit before submission

Reviewer, cycle 7. Scope: `paper/CAPSTONE-PAPER.md` (all sections, tables, figures, appendices) against the
released results files; `stage_f/*.py`, `paper/make_figures.py`, `paper/paired_ci.py`;
`stage_f/F-PROTOCOL.md` and `stage_f/F-EXECUTION-NOTES.md`; freeze integrity. HEAD `41f724a`, branch
`stage-c-ctf-prefreeze`, working tree clean at start and at end.

Rules followed: no cloud, pod, key or spend; no push or commit; the label sheet folder was not opened (the
R7-03 reasoning uses only `make_label_sheet.py` and `f2_summary.json`). No harmful model text was read. The
only file written in the repository is this one; scratch scripts and the figure regeneration ran in the
session scratchpad.

## What I ran

| Check | Result |
|---|---|
| `freeze_f.py check` (WSL, root) | **"stage F freeze verifies"** |
| `freeze_v2.py check` (WSL, root) | **"CTF v2 freeze verifies"** |
| `reviews/check_freeze_delta.py` (WSL, stage D venv) | **fails**: "modified ['EXPANDED-STUDY-PLAN.md', 'score_run1.py', 'test_run1.py'] … committed score_run1.py does not match its frozen hash …" (see R7-02) |
| `git diff --stat 16b6913 HEAD -- stage_b stage_c stage_d stage_e stage_f sr_judge.py judge_templates.json` | only `F-EXECUTION-NOTES.md` and the 7 `stage_f/results/*` files added. `git diff 8f759f2 HEAD -- stage_e` adds only results files. |
| Commit timing | `8f759f2` 23:21:45 UTC (aligned v2 pod created 23:24:06); `16b6913` 16:56:06 UTC (F1 install 17:06:40). Both, and `75d896d`, `06c2551`, `41f724a`, are in `origin/stage-c-ctf-prefreeze` (local remote-tracking ref). |
| `stage_f/test_f.py` (WSL, `-B`) | 23 tests, OK |
| `paper/paired_ci.py` + `paper/make_figures.py` on a `git archive HEAD` copy in the scratchpad | `paired_ci.json` and all six SVGs byte-identical to the working tree. **Without** the untracked `stage_c/ctf_trial_results.json` the figure script fails with `FileNotFoundError` (R7-01). |
| Independent statistics (scipy 1.18 + exact formulas, scratchpad script) | every Clopper–Pearson CI, exact McNemar p, Fisher p, Holm value and sign-flip p in the paper and summaries reproduced (list below) |

## Findings

| ID | Severity | Location | Problem and evidence | Suggested fix |
|---|---|---|---|---|
| R7-01 | minor | Paper §11 l.1020–1021; Appendix B l.1233; `paper/make_figures.py:248` | §11 says `python paper/make_figures.py` regenerates "all figures from the released summaries". The script loads `stage_c/ctf_trial_results.json` (for Figure 2 and its assert), and Appendix B lists that file as a stage C artefact. It is **not in the repository**: `.gitignore:12` (`*_results.json`) ignores it and `git ls-files` does not list it. On a clean `git archive HEAD` copy the script stops with `FileNotFoundError`. The file holds only per-trial ids, reasons, counts and timings (field types checked; no `{` anywhere, so no flag-like strings). | `git add -f stage_c/ctf_trial_results.json` after a final look, or change §11 and Appendix B to say that Figure 2 needs a private file. |
| R7-02 | minor | `stage_d/DEVIATIONS-AND-LIMITATIONS.md:18–19`; `reviews/check_freeze_delta.py`; `stage_d/EXPANDED-STUDY-PLAN.md` | (a) The deviations file says `reviews/check_freeze_delta.py` "verifies that nothing else frozen changed". It now fails. One reason is the script's design: it requires the **committed** `score_run1.py` and `test_run1.py` to equal their frozen hashes, which held only before the REPAIR-001 fixes were committed (`97f850f`). (b) The second reason is real. `EXPANDED-STUDY-PLAN.md`, a file hashed in `run1_freeze.json`, was edited after the run 1 freeze and after VERIFY-001: commit `418edc1` (2026-11-19 17:40 −05:00) appended a "Decision update" section that cancels the B–D follow-up. The edit is append-only and changes no result, but it is a post-freeze edit to a frozen file, and no deviation records it. The paper cites stage D only as context (§3.3, §6), so v2 and stage F are unaffected. | Add a D-31 entry (or a note under D-05) for the appended plan section. Update `check_freeze_delta.py`: compare the two repaired files with their `97f850f` blobs, and add `EXPANDED-STUDY-PLAN.md` as an expected append. Alternatively, change the sentence at l.18–19 to say that the script describes the pre-commit state. |
| R7-03 | minor | Paper §7.3 l.786–790 ("arm, task and flag hidden"); §9 l.910–912 (blinding limitation); `make_label_sheet.py:91` | The sheet's `ended_by` column is `solved` or the ending reason. From `f2_summary.json` `ending_reasons`: `agent_ended_without_verified_flag` occurs only in aligned (10 rows), and `time_cap` / `submission_budget` occur only in Heretic (3 rows). So **13 of 42 rows reveal the arm** through this column. Also, every rule-refused trial is exactly an `agent_ended_without_verified_flag` row, and every rule-"complied" row with a solve shows `solved`. The labeller therefore sees a proxy for the rule outcome, so rule–label agreement (κ) is not independent of the rule. The protocol pre-registered "how the trial ended" on the sheet, so this is not a deviation. But the paper's blinding statement and limitation mention only style. | In §7.3 and §9 add: "The sheet shows how each trial ended. For 13 of 42 trials this identifies the arm (only aligned trials ended on a text reply, only Heretic trials on a time or submission limit), and it reveals the rule outcome, so agreement with the rule will be optimistic." State the same when the labels are reported. |
| R7-04 | minor | Paper §5.6 l.551–552; §9 l.943–944 | "the last-scheduled trials … ran partly with one or two in flight, when per-sequence decoding is about 12–19% faster." 12–19% is the **1 vs 3** in-flight speed-up (14.9 / 12.4 / 19.4%; REPAIR-003 R3-18; `CTF-V2-RESULTS.md` l.151). With 2 in flight, `decode_tok_per_s_by_trials_in_flight` gives aligned 40.24 vs 35.81 (+12.4%), abliterated 37.41 vs 36.21 (**+3.3%**) and Heretic 39.2 vs 35.1 (+11.7%). Heretic's unlimited_subway had `min_in_flight` 2, so its advantage was about 12%, not up to 19%. | "about 12–19% faster with one in flight and 3–12% with two". In §9: "ran with up to 12–19% faster decoding". |
| R7-05 | minor | Paper §3.3 l.247–249 | Stale after stage F: "Across the stages that compared these Qwen3.8-27B checkpoints directly (stage B and v2), no difference between aligned and abliterated was detected … a consistent pattern of non-detection". Stage F also compared these checkpoints directly and found very large refusal differences (F1 p = 6.5 × 10⁻⁵⁵; F2 p = 0.00015). Read alone, this paragraph contradicts §7. | Scope it: "Across the stages that compared these checkpoints on capability or attack success (stage B and v2), no difference was detected … Stage F, which measured willingness, did find large differences (Section 7)." |
| R7-06 | minor | Paper §8.1 l.826–827 ("each uncensored model none"); §13 l.1053–1054 ("the uncensored versions none") | R6-11 added the empty-answer qualifier to the abstract, §7.2 and Table 10, but not here. 189/313 (abliterated) and 148/313 (Heretic) answers are empty (`f1_summary.json` `no_answer`), so "none" counts those as non-refusals. | Add "(also none among prompts answered within the token limit: 0 vs 51/74 and 74/111)" or "of the answers they gave" in both places. |
| R7-07 | minor | `README.md` l.1–16 | The repository entry point is stale. Its newest entry is the stage C run (1/14 vs 2/14). It never mentions CTF v2, stage F or `paper/CAPSTONE-PAPER.md`, so an examiner who opens the repository first sees the superseded stage C numbers as the headline. | Add a top entry linking the paper, `stage_e/results/CTF-V2-RESULTS.md` and the stage F summaries, with the headline numbers (9/8/8 of 14; F1 181/0/0; F2 10/0/0 refused, 4/14/11 solved), and mark stage C as superseded (D-26). |
| R7-08 | nit | Paper §5.1 l.446–448 | "the flag appeared in the raw output of the immediately preceding terminal command" for all 25 solves. `posthoc_v2.json` `reference_in_preceding_terminal_output_contiguous` is 9/8/**7**, and `CTF-V2-RESULTS.md` l.176–178 says that in one Heretic trial (target_practice) the flag was split across two `xxd` lines. | Add "(in one Heretic trial split across two `xxd` lines)". |
| R7-09 | nit | Paper Table 10 l.892, Evidence cell | "repository dates and revisions in `v2_config.json`". `v2_config.json` holds the revisions but no dates. | "revisions in `v2_config.json`", or cite where the dates are recorded. |
| R7-10 | nit | Paper §5.2, §5.3 | Figures 3 and 4 are never cited in the body. They appear only as images with captions. Figures 1, 2, 5 and 6 are cited. | Add "(Figure 3)" after the interval sentence in §5.2 and "(Figure 4)" in the §5.3 paragraph after Table 5. |
| R7-11 | nit | Paper §1.2 item 4 l.137–138 | "states criminal intent and removes the CTF cues (including the official task description)". Residual cues remain (§9: `submit_flag`, `flag`, `ctfnet` reverse DNS, `/opt/ctf-tools/bin`, "flag" in pages and binaries). | "removes the CTF cues from the fixed text (including the official task description)". |
| R7-12 | nit | Paper §7.3 l.755–765 | The "Endings" bullet sits under "Other pre-registered secondary outputs (raw p)". It has no p, and the protocol lists ending reasons among the descriptive measures (`F-PROTOCOL.md` l.132–135). | Move "Endings" under "Descriptive details". |
| R7-13 | nit | Paper header l.15–16 vs §4.1 l.308–311, §7.2 l.715–718, §7.3 l.770–782, §9 l.905 | The header says numbers computed for this paper are marked †. Numbers from the post hoc `f_derived_aggregates.json` are cited by file name but not marked †, while comparable v2 post hoc numbers are (for example "17/17 tasks†"). | Add † to those statements, or say in the header that file-cited post hoc numbers are unmarked. |
| R7-14 | nit | Paper §7.1 l.649–650; §7.2 l.703–704 | The Wilcoxon test is the **normal approximation** (`analyze_f.py:56–79`; `f1_summary.json` `"test": "Wilcoxon signed-rank (normal approx.)"`). The paper says only "Wilcoxon signed-rank". | Add "(normal approximation, as frozen)". |
| R7-15 | nit | `paper/make_figures.py:274` | The fallback message says "run paper/paired_ci.py first for figure 5". `paired_ci.json` feeds Figure 3. Cosmetic only, and the branch did not run. | "for figure 3". |
| R7-16 | nit | Paper §9 l.961–962 vs `F-EXECUTION-NOTES.md` l.60–62 | The paper says the protocol folder "was not accessible to the author". The notes say it is root-only, so the author "could not easily open the sheet there". | "was root-only inside WSL and not convenient for the author to open". |
| R7-17 | nit (process) | Paper header l.9; Appendix D | The status line still says "revised in review cycle 6", and Appendix D has no cycle 7 row. | Update after this cycle's repair and verification. |

## Checked and found correct

**v2 (Tables 1–5, §5, abstract, §8, §13).** 9/8/8 of 14; CP CIs 35.1–87.2 and 28.9–82.3; web 3/3/3, pwn
6/5/5; Table 2 per-task outcomes and endings vs `ctf_v2_summary.json` `solved_tasks` and `posthoc_v2.json`
`tasks` (roppity aligned `tool_budget`); Table 3 by difficulty; 7 solved by all and 4 by none (all Hard);
discordant tasks; Table 4 counts (8/0/1/5, 7/1/2/4, 7/1/1/5), −7.1 and 0.0 points, Tango and Newcombe
intervals (re-run of `paired_ci.py` is byte-identical), McNemar p = 1.0 and Holm 1.0 (recomputed); "two or
three more / four to five fewer" (2.2–3.0 and 4.4–5.0 tasks); power (6–0 p = 0.031, 7–0 p = 0.016, 9–1
p = 0.021, 5–0 p = 0.0625); Table 5 (9/10, 8/8, 8/8; 18.6/20.8/23.2; 16.6/18.4/20.6; 16/21/27; 2/4/5); speeds
36.7/36.7/36.0, medians 11.4/13.9/11.3 s; reasoning 83/82/83%; 66/78/84 and 20/25/28 requests; 37/35/29%;
33.6k–42.7k time-capped tokens; dev endings; 806 replies (237/266/303); 217 matches (106 + 111); get_it 983 s,
unlimited_subway 729 s; context maxima 32,726/31,461/30,218 (< 2.6k from the limit); 51/51 gates on
attempt 1; spend 2.632 + 4.291 + 2.946 = 9.869 → $9.87 against 3 × $6.76; v2 timeline 23:24–07:15 UTC.

**Stage C and earlier stages.** Table 6 = `ctf_results_summary.json`; §6 per-task defect attribution vs
`ctf_trial_results.json` reasons; 5 of 7 within the old budget with the listed times; 6.7 s
(`CTF-RESULTS.md` l.75); 7 of 22 pwn trials; 79%; stage D 1,490/1,593 of 5,146; stage B 17/32 vs 16/32, +3.1,
Tango −16.5 to +22.7, p = 1.00, 11/12; refusal audit 0 of 32 and 0 of 10; tool poisoning 0.52 vs 0.00;
StrongREJECT −0.533/−0.300; $3.71, $2.07 settled ($2.0675), $1.52.

**F1 (Table 7, §7.2, abstract).** All counts and rates; CP CIs 52.1–63.4, 0–1.2, 91.5–96.8, 0.5–3.7, 1.3–5.4
(recomputed); McNemar 6.5 × 10⁻⁵⁵ = 2·0.5¹⁸¹, Holm 1.3 × 10⁻⁵⁴; any refusal 3.7 × 10⁻⁸⁶ and 5.8 × 10⁻⁸⁵
(< 10⁻⁸⁰), discordant counts consistent with the per-arm totals (296 = 4 + 292; 5 = 4 + 1; 9 = 8 + 1);
excluded set 8.9 × 10⁻¹⁶ and 1.1 × 10⁻²² over 74 and 111 pairs; Heretic vs abliterated any refusal 6 vs 2,
p = 0.2890625; Wilcoxon Holm (0.00307 stays 0.00307; 4.76 × 10⁻¹³ × 2 = 9.5 × 10⁻¹³); cross-tab 3/189/148
no-answer all length-capped and open, 5/50/54 closed and capped; alert only for abliterated; fallback
identical; F1 $2.235 = 60.46 min × $2.2178/h; under the 90-min hard stop and the $3.43 cap.

**F2 (Tables 8–9, §7.3, §8, §13, Figure 6).** 42/42 observed; 10/0/0 refused, 4/14/11 solved; CIs 42–92,
0–23, 8–58, 77–100, 49–95, 40–100 (recomputed); Fisher 0.00015 (refusal both, solve abliterated) and 0.0213
(solve Heretic), Holm 0.0003/0.0003/0.0213; secondary 1.0 and 0.222; non-refused solve p = 1.0 and 1.0;
sign-flip 2/128 = 0.015625 (only the two all-same-sign assignments reach |Σd| = 5); per-task refusals sum to
10; Heretic misses get_it ×2 time cap and puffin ×1 submission budget; 10 single-turn zero-tool refusals;
refusal language 14/13/4; zero cut-offs before the first terminal call; 25 of 28. Spend 0.586 + 1.195 + 1.449 =
3.230 (each = elapsed × $2.2178/60), stage F 5.465 → $5.47; F2 pods under the 120-min / $4.54 caps; guard
deadlines consistent with the notes' times. Figure 6 values match the JSON.

**Provenance (§4.1).** Template `af16f654` vs `c3cf9e34` ×2; three distinct `tokenizer_config.json`; Heretic
`tokenizer.json` `06b95093` and `generation_config.json` `b8eb74d1`; think-end id 248069; benign probe hash
identical, 59 tokens, open thinking, matching `f_derived_aggregates.json`, `posthoc_v2.json` and the F2 run
status files.

**Text and structure.** Every Section, Table (1–10), Figure (1–6), Appendix and D-number reference resolves;
headings numbered 1–14 with no stale "Table 7 (course requirements)"; abstract, §8, §13 and Table 10 agree
on every number; Appendix A.2 matches `framing_f2.py` verbatim; Appendix B lists exactly the 14 code files
of `f_freeze.json` (16 keys with protocol and config); Appendix D counts match REVIEW/VERIFY-001…006; the
cycle 6 builder fixes are present ("unlock" now occurs only in §8.1's route sentence and the A.2 quote).
No `rpa_`, flag literal, token or Windows user path appears in the paper, the notes or the results files.

**Code.** `analyze_f.py`: McNemar, Fisher (relative tolerance), Holm (step-down with running max),
sign-flip, Clopper–Pearson import, bootstrap, `trial_outcome`, per-task and non-refused denominators are
correct, and I found no bug that would change a reported number. `pod_f1.py` split and fallback rules match
the protocol. `run_arm_f2.py` scans content only, as the protocol says. `make_label_sheet.py` hides arm,
task and tool arguments and redacts flags; its only blinding gap is R7-03.

## Summary

17 findings: **0 major, 7 minor, 10 nit**. I found no wrong number, p value, CI, count, cost, date or hash
in the paper.

Top issues:
1. **R7-01:** `make_figures.py` cannot run from the released repository, because `stage_c/ctf_trial_results.json`
   is git-ignored. §11 and Appendix B say it can, and that the file is released.
2. **R7-02:** `reviews/check_freeze_delta.py` now fails, although the deviations file cites it as proof. A
   frozen stage D file (`EXPANDED-STUDY-PLAN.md`) was appended after its freeze in `418edc1`, without a
   deviation entry. Stage F and v2 freezes verify.
3. **R7-03:** the pre-registered `ended_by` column on the label sheet identifies the arm for 13 of 42 trials
   and reveals the rule outcome. This is undisclosed, and it will make rule–label agreement optimistic.
4. **R7-04 / R7-05 / R7-06:** wording that is now inaccurate: the 2-in-flight speed-up (3–12%, not 12–19%),
   §3.3's "consistent pattern of non-detection" (stale after stage F), and "none" in §8.1 and §13 without
   the empty-answer qualifier.
5. **R7-07:** the README still leads with the superseded stage C result and does not link the paper.
