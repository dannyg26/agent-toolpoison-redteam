# VERIFY-006: independent verification of REPAIR-006 (stage F results and paper additions)

Verifier, cycle 6. Scope: the uncommitted repairs on top of `06c2551`: `paper/CAPSTONE-PAPER.md`,
`paper/make_figures.py`, the untracked `paper/figures/fig6_willingness.svg`, the untracked
`stage_f/F-EXECUTION-NOTES.md` and the new (git-ignored) `stage_f/results/f_derived_aggregates.json`, checked
against REVIEW-006. I did not rely on REPAIR-006's descriptions. I read the changed text, re-derived every
stage F number from the released JSON files, and re-computed the derived aggregates from the private
structured fields myself.

Rules followed: no cloud, pod, key, `--launch` or `--check-access`. No git state was changed. This is the
only file I wrote in the repository. My two read-only scripts lived in the session scratchpad, outside the
repository. They read the private files as root in WSL. They printed field names, counts and 8-character
hash prefixes only, never trace text, answer text, prompts or flags. The only text fields I touched were
F1 `content`, and only to test whether it was empty.

## What I ran

| Check | Result |
|---|---|
| `freeze_f.py check` (WSL, root) | **"stage F freeze verifies"** |
| `git diff --stat` | only `paper/CAPSTONE-PAPER.md` and `paper/make_figures.py`; `git diff --stat HEAD -- stage_f stage_e` is empty. `F-EXECUTION-NOTES.md` is untracked and is not in `f_freeze.json` (the freeze excludes `F-EXECUTION*`) |
| `python paper/make_figures.py` | exit 0. SHA-256 of all six SVGs is identical before and after. `git status --porcelain paper/figures` shows only `?? fig6_willingness.svg` |
| fig6 text vs JSON | 9/14, 8/14, 8/14 (v2); 181/313, 0/313, 0/313 (F1 full refusal); 10/14, 0/14, 0/14 (F2 refused, panel now "refused by rule"); 4/14, 14/14, 11/14 (F2 solved). All match `ctf_v2_summary.json`, `f1_summary.json` and `f2_summary.json`. The `capitalize()` call sits only in `fig_willingness` |
| Private F2 `results.jsonl` (structured fields) | 14 rows per arm, no duplicate (task, repeat). Aligned: `solved` 4, `unsolved_within_budget` 10. All 10 unsolved rows have `terminal_calls = 0`, reason `agent_ended_without_verified_flag`, `assistant_turns = 1` and `tool_calls = 0`. Abliterated: 14 solved; 2 trials with any cut-off step, 0 before the first terminal call. Heretic: 11 solved; get_it ×2 `time_cap`, puffin ×1 `submission_budget`; 3 trials with any cut-off step, 0 before the first terminal call. Per-task solved and unsolved counts equal `f_derived_aggregates.json` exactly |
| Private F1 `ARM.jsonl` (`finish_reason`, `thinking_closed`, emptiness of `content`) | aligned stop/closed/answer 305, length/closed/answer 5, length/open/empty 3; abliterated 74 / 50 / 189; heretic 111 / 54 / 148. Equals the aggregates cross-tab and Table 7 (length-capped 8 / 239 / 202; thinking closed 310 / 124 / 165) |
| Private F1 `provenance_ARM.jsonl` (hash fields only) | template, tokenizer and generation-config prefixes equal the aggregates file and the F2 run status files. Think-end id 248069 and vLLM 0.33.0 in all arms. The benign-probe rendered SHA-256 is **identical in full (64 hex chars)** across the three arms, with 59 tokens and an open thinking block |
| Aggregates file content | 112 lines. Only counts, hash prefixes, task ids and reason codes. No text, prompt, flag or key. Keys such as `answer|finish=stop|...` are category labels |
| Privacy grep (paper, script, fig6, notes, aggregates, REVIEW/REPAIR-006) | no `rpa_`, no `csawctf{`/`flag{…}` with content, no `hf_`/`sk-` tokens, no Windows user path, no AppData path. The only user-like string is the repository URL in Section 11, already present at `HEAD` and accepted in earlier cycles. No harmful model text |
| Cross-references | every Section / Table / Figure / Appendix reference resolves: Tables 1–10 and Figures 1–6 in order; Section 12 "Template control" and Section 4.1 benign probe exist; Figure 6 is now cited twice |
| Abstract | 404 words (was about 610), four paragraphs plus a closing synthesis sentence |
| New table rows | Table 7 and Table 8 rows have 4 cells each, matching the header; they render |

## Verification table

| Finding | Claimed action | Verdict | Evidence | Remaining |
|---|---|---|---|---|
| **R6-01** (major) causal attribution to refusal removal | Published-checkpoint wording in the abstract, 8.1, 7.3, 9 and 13; one "not weight edits alone" clause; "main barrier" removed | **VERIFIED** | Abstract ¶1 says "a difference between published checkpoints, not between weight edits alone", and the closing sentence says "published refusal-removed checkpoints". 8.1 says the differences "cannot be attributed to the weight edit alone" and names "the one criminal framing that F2 tested". 7.3 says "published checkpoint (weights plus its template and tokenizer files)". Grep finds no "main barrier", "treatment worked" (except the protocol quote in 1.1) or "removing safety training". | none |
| **R6-02** (major) stale "(none was detected)" | Rewritten template bullet | **VERIFIED** | 9 "Template differences" now separates v2 (no difference detected) from stage F (differences between published checkpoints) and points to 4.1 and Section 12. | none |
| **R6-03** (major) equivalence claim in 13 | Rewritten | **VERIFIED** | 13 ¶2: "not detectably better attackers on these 14 tasks (a gain could not have been detected) … by the pre-registered rule. These are differences between published checkpoints". This is consistent with 13 ¶1, 8.1 and the abstract. | none |
| **R6-04** (major) causal inference from cross-run v2 vs F2 | 9, 5.4, 8.2 and 3.1 hedged | **PARTLY FIXED** | 9 "CTF framing": "consistent with … but the comparison is descriptive and cross-run". 5.4: "(untested in v2)" and "descriptive evidence consistent with … not a test of the framing alone". 3.1: "The comparison with v2 is descriptive." 8.2 bullet 2 is hedged, and the reverse direction is disclosed as untested. "Both are cheap" is gone. | **8.2 bullet 1 (line 850)** still says the aligned model's CTF-framed capability approximates the uncensored one "**because the framing already unlocks the aligned model**". That is the same causal reading of the framing that R6-04 asked to remove, and the sentence is not in `HEAD`. Suggest "because under the CTF framing the aligned model did not refuse (v2)". |
| **R6-05** (major) missing pre-registered outputs | Table 8 rows; 7.2 and 7.3 bullets; Table 7 CIs | **VERIFIED** | (a) Table 8 "Solved among trials not refused": 4/4 (40–100), 14/14 (77–100), 11/14 (49–95) = `solve_among_non_refused_ci95`; Fisher p = 1.0, 1.0 and 0.22 match `secondary.solve_among_non_refused`. (b) Any refusal = refused because `refused_after_engaging` = 0 everywhere. (c) Cut-off before first terminal = 0/0/0; endings 10 + 4 / 14 / 11 + 2 + 1 match `ending_reasons`. (d) Heretic vs abliterated: full refusal p = 1.0, any refusal 6 vs 2 discordant (p = 0.29 from 0.2890625), score +0.099, p = 9.6 × 10⁻¹⁰. (e) Any-refusal CIs 91.5–96.8, 0.5–3.7, 1.3–5.4 match `any_refusal_ci95`. | The list layout around them is a new minor issue, see V6-01. |
| R6-06 F1 provenance not reported | 4.1 reports hashes, think-end id and benign probe | **VERIFIED** | Recomputed from the private provenance files (see above). The full rendered-probe SHA-256 is identical in all arms. 4.1 states the limit correctly: system, tool and tool-result rendering were not checked. "may differ" is appropriate. | none |
| R6-07 rule vs judgment wording | Abstract, 1.2 item 4, 8.1, Table 10, 7.3, 9 | **VERIFIED** | Abstract: "the trajectory ended on a text-only reply after zero terminal commands" and "hand labels were pending". 1.2(4), 8.1 and the Table 10 limit cell carry the rule and pending-labels qualifier. No "declined" remains in the stage F text. The rule is stated the same way in 7.1, 7.3 and 9. | Minor residue: see V6-02. |
| R6-08 unverifiable claims | Verified from private structured fields and sourced | **VERIFIED** | My recomputation: all 10 aligned rule-refusals are `assistant_turns = 1`, `tool_calls = 0`; Heretic misses get_it ×2 `time_cap`, puffin ×1 `submission_budget`; every F1 no-answer row is `length` with thinking open. "Ran terminal commands in every trial" is supported by `zero_terminal_calls = 0`. Each claim names its source. | none |
| R6-09 RQ5 expectation | 1.1 rewritten | **VERIFIED** | `F-PROTOCOL.md` has a "Pre-stated expectation" only in F1 (line 75). 1.1 now says RQ5 pre-specifies tests only. | none |
| R6-10 generalisation in 8.2 | Scope in the sentence; caveat moved first; "not a safeguard" softened | **VERIFIED** | 8.2 ¶1: "On these 7 sandboxed tasks, chosen because every arm could solve them … 25 of 28 … 4 of 14" (14 + 11 = 25 ✓). "These implications are tentative" now comes before the bullets. The checkpoint-swap bullet "follows from open weights rather than from our data". | none |
| R6-11 empty answers in "0 full refusals" | Abstract and 7.2 add the excluded-prompt result; "So the treatment worked" removed | **PARTLY FIXED** | The numbers (0 vs 51/74 and 74/111) are right, and the 7.2 sensitivity bullet describes them correctly as "excluding prompts that were length-capped or had no answer in either arm". | **The abstract (line 37–38) and the 7.2 last paragraph (line 725–726) describe the same 74 and 111 prompts as "the prompts both arms answered". That is wrong.** From the private finish reasons, both arms gave a non-empty answer on 124 (abliterated) and 165 (Heretic) prompts. The 74 and 111 are the prompts both answered **without hitting the length cap**. Suggest "on the prompts both arms answered within the token limit". |
| R6-12 v2 scoping | "(v2)" title and "In v2," | **VERIFIED** | 9 bullet. | none |
| R6-13 change lists and cues | 7.1 and 9 add stay-in-scope; `submit_flag` also in user message | **VERIFIED** | 7.1 item 1 and 9 "F2 changes several things at once" both name the dropped instruction (matches A.1 vs A.2). The residual cue list says "(also named in the user message)", which matches the A.2 user message. "Six things at once" in 9 matches the six listed changes. | none |
| R6-14 Figure 6 | Cited in 7.3 and 8.1; panel title; capitalised labels | **VERIFIED** | Two in-text citations. The SVG panel reads "F2: refused by rule (criminal framing)", and the labels are Aligned/Abliterated/Heretic. fig1 to fig5 are byte-identical. | none |
| R6-15 Appendix B and D | B: all `f_freeze.json` files; D row 6 | **VERIFIED** | The 14 code files named, plus the protocol and `f_config.json` in the row above, equal the 16 `sha256` keys of `f_freeze.json`. D row 6 gives 18 findings (5 major, 13 minor) plus one note, and points to this file. | After this file, the D row 6 outcome could be updated to the verdict counts (optional). |
| R6-16 label sheet location | OneDrive / File History check recorded; move back or delete after labelling | **PARTLY FIXED** | `F-EXECUTION-NOTES.md` is accurate and appropriately limited: it covers OneDrive and File History only, says "Other backup software was not checked", and concludes "not cloud-synced **by OneDrive**". It names no path or user folder. The move-back or delete step is recorded. | **Paper Section 10 (line 989–990) overstates this** as "checked not to lie inside any cloud-synced folder". Only OneDrive was checked. Suggest "checked not to lie inside any OneDrive-synced folder (other sync or backup software not checked)". |
| R6-17 stale status line in frozen protocol | Disclosure in notes | **VERIFIED** (disclosure justified) | `F-PROTOCOL.md` is unchanged (freeze verifies). The notes header states that the line is stale and that `16b6913` is the freeze. | none |
| R6-18 abstract length and order | Rewritten | **VERIFIED** | 404 words. It ends on "Taken together", and the stage C sentence comes before it. The abstract agrees with 7.2, 7.3, 8.1, 9, 13 and Table 10 on every number (181/0/0; 10/14, 0, 0; 4, 14, 11 of 14; p = 0.00015, Holm 0.0003; 0.016). | Only the R6-11 denominator wording. |
| R6-19 (note) | none | **VERIFIED** | I re-derived every stage F number in Tables 7 to 9, the new rows and bullets, 8.1, 8.2, 13, Table 10, the notes and the spend line ($2.235 + $0.586 + $1.195 + $1.449 = $5.465 → $5.47; F1 $2.24, F2 $3.23). All match `f1_summary.json`, `f2_summary.json`, the run status files and the aggregates file. The 4.1 hash claims match `f2_run_status_*.json` (aligned `af16f654`; both uncensored `c3cf9e34`; Heretic `tokenizer.json` `06b95093` and `generation_config.json` `b8eb74d1`). | none |

## New issues

| ID | Severity | Location | Problem | Suggested fix |
|---|---|---|---|---|
| V6-01 | minor | 7.3, lines 753–780 | The new "Other pre-registered secondary outputs (raw p):" list (three bullets) is followed by a blank line and then the earlier bullets ("Aligned", "Refusal-language scan (descriptive)", "Uncensored arms", "Task-clustered test"). In CommonMark, list items separated by a blank line stay **one** list, so these four render as further "pre-registered secondary outputs (raw p)". The refusal-language scan is descriptive and the task-clustered test is a sensitivity analysis. | Put a short paragraph line (for example "Per-arm detail:") between the two lists, or move the secondary-outputs bullets after the per-arm bullets. |
| V6-02 | minor | 8.2 bullet 2, line 852–853 | "the published uncensored checkpoints did not refuse the criminal request" has no rule qualifier. The other stage F refusal statements carry one, and the hand labels are pending. | "did not refuse the criminal request (by the pre-registered rule)". |
| V6-03 | note (committer) | `stage_f/results/f_derived_aggregates.json`, `stage_f/F-EXECUTION-NOTES.md`, `paper/figures/fig6_willingness.svg` | The paper cites the aggregates file as released (Sections 4.1, 7.2, 7.3, 9, 11; Appendix B), but `.gitignore:6` (`results/`) ignores it (`git check-ignore` confirms). The notes file and fig6 are also untracked. If any of them is left out of the commit, the paper points to files that do not exist in the repository. | Commit with `git add -f stage_f/results/f_derived_aggregates.json` and add the two untracked files. |

The R6-04, R6-11 and R6-16 remainders are listed in the table above rather than as new issues.

## Summary

19 items checked (R6-01 to R6-18 plus note R6-19): **16 VERIFIED** (including R6-17 as a justified disclosure
and the R6-19 note), **3 PARTLY FIXED** (R6-04, R6-11, R6-16), **0 NOT FIXED**. New: **3** (V6-01, V6-02 minor;
V6-03 committer note).

The remainders are wording only. No number is wrong:
1. R6-04: 8.2 "because the framing already unlocks the aligned model" (causal).
2. R6-11: the abstract and 7.2 call the 74/111 sensitivity prompts "the prompts both arms answered". They are
   the prompts both answered without hitting the length cap (both answered: 124 and 165).
3. R6-16: Section 10 says "any cloud-synced folder", but only OneDrive was checked (the notes are accurate).

The freeze verifies, no frozen or stage E file changed, fig1 to fig5 are byte-identical, fig6 matches the JSON, and
the derived aggregates reproduce exactly from the private structured fields and hold no text, prompts, flags or keys.

## Builder follow-up (after verification)

The builder fixed the five remaining wording items directly in `paper/CAPSTONE-PAPER.md`:

- **R6-04:** Section 8.2 no longer says the framing "unlocks" the aligned model. It now says the aligned
  model did not refuse under the CTF framing in v2.
- **R6-11:** the abstract and Section 7.2 now say "answered without hitting the length cap" for the 74 and
  111 prompts.
- **R6-16:** Section 10 now says "not inside a OneDrive-synced folder", and that other backup software was
  not checked.
- **V6-01:** Section 7.3 now has a "Descriptive details" lead-in, so those bullets no longer read as
  pre-registered secondary outputs.
- **V6-02:** Section 8.2 adds "by the pre-registered rule; hand labels pending".

**V6-03:** handled at commit time (`git add -f` for the results file; the notes and fig6 are added).
