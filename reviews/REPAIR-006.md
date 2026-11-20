# REPAIR-006: repairs after REVIEW-006 (cycle 6)

Repairer, cycle 6. I changed only `paper/CAPSTONE-PAPER.md`, `paper/make_figures.py` (and the regenerated
`paper/figures/fig6_willingness.svg`) and `stage_f/F-EXECUTION-NOTES.md`. I added one aggregate file,
`stage_f/results/f_derived_aggregates.json`, and this report. No frozen file was edited. Nothing is
committed. There were no pods, cloud calls or API keys.

**Verification baseline:**
- `python3 freeze_f.py check` (WSL, root) prints **stage F freeze verifies**.
- `python paper/make_figures.py` exits 0. `git status --porcelain paper/figures` shows only the untracked
  `fig6_willingness.svg`, so fig1 to fig5 are byte-identical.
- Privacy grep over every changed or added file (`rpa_`, `csawctf{`, `flag{`, Windows user paths): no
  hits. The only user-like string is the repository URL in Section 11, which was already present.
- Abstract: about 400 words (was about 610), four paragraphs plus a closing synthesis sentence.

## New derived file (R6-06, R6-08)

`stage_f/results/f_derived_aggregates.json` holds counts and 8-character hash prefixes only. It has no
model text, no prompts and no flags. I computed it as root in WSL from **structured fields only** of the
private files:
- F1 `provenance_ARM.jsonl` (hashes, think-end id, benign-probe rendered hash, token count, think-open flag);
- F1 `ARM.jsonl` (`finish_reason`, `thinking_closed`, and the frozen willingness class, computed in memory
  by the frozen rule and never printed);
- F2 `results.jsonl` (`task_id`, `repeat`, `solved`, `reason`, `tool_calls`, `terminal_calls`,
  `assistant_turns`, `cutoff_steps`), with the frozen `analyze_f.trial_outcome`.

Every count agrees with `f1_summary.json` and `f2_summary.json` wherever they overlap. The script was a
temporary scratch file outside the repository. **Note for the committer:** `.gitignore` line 6 (`results/`)
ignores the new file, so it needs `git add -f`, as was done for the other results files.

Facts it establishes:
- F1: every no-answer prompt (3 / 189 / 148) was length-capped with its thinking still open. The other
  length-capped generations (5 / 50 / 54) had closed their thinking.
- F1 provenance: the same template and tokenizer hashes as the F2 run status files, and the same
  think-end id in every arm. The benign probe rendered identically in all three arms (same SHA-256 prefix
  `81e8e38d`, 59 tokens, ends with an open thinking block).
- F2: all 10 aligned rule-refusals had exactly one assistant turn and zero tool calls. Heretic's misses
  were get_it × 2 (`time_cap`) and puffin × 1 (`submission_budget`).

## Findings

| ID | Action | Files / sections | Notes |
|---|---|---|---|
| R6-01 (major) | Fixed. The abstract now says in its first paragraph that each arm is the checkpoint as published, including its template, so differences are between published checkpoints, not weight edits alone. The closing sentence now reads "the published refusal-removed checkpoints were not detectably more capable, but under openly criminal framing they attempted attacks that the aligned model usually did not". In 8.1, "Refusal removal ... removed the aligned model's main barrier" is replaced by the published-checkpoint wording, and "main barrier" is dropped. 8.1 now adds the clause "cannot be attributed to the weight edit alone" and names "the one criminal framing that F2 tested". In 13, "removing safety training" is replaced (see R6-03). F1 in 8.1 now reads "the published uncensored checkpoints refuse less" instead of "the treatment works". 7.3 and 9 now say "published checkpoint" where they said "checkpoint". | Abstract; 8.1; 7.3 last paragraph; 9 F2 bullet; 13 | I also changed 8.1 ¶1 "no added capability from refusal removal" to "in the refusal-removed checkpoints". |
| R6-02 (major) | Fixed. The template bullet now reads: in v2 no between-arm difference was detected; in stage F the large refusal differences are between published checkpoints (weights, template, tokenizer configuration), not weights alone. It points to Section 4.1 (benign probe) and to Section 12, "Template control". | 9, "Template differences" | |
| R6-03 (major) | Fixed. Section 13 now reads: "the published refusal-removed checkpoints were not detectably better attackers on these 14 tasks (a gain could not have been detected), but they were willing to attack where the aligned model usually did not, by the pre-registered rule. These are differences between published checkpoints, not between weight edits alone." | 13 ¶2 | |
| R6-04 (major) | Fixed. In 9 "CTF framing", the causal sentence is replaced: F2 changed six things at once, removing the CTF framing among them, and found 10/14 by the rule; "consistent with the framing suppressing refusals in v2, but the comparison is descriptive and cross-run". In 5.4: "(untested in v2)" and "Stage F later gave descriptive evidence consistent with this explanation ... not a test of the framing alone". In 8.2, the bullet now says the cross-run contrast is descriptive and that the reverse direction (re-adding a CTF framing) was not tested. "Both are cheap" is removed. I also changed 3.1 "Stage F tests this directly" to "examines this ... The comparison with v2 is descriptive". | 9; 5.4 ¶2; 8.2 bullet 2; 3.1 | |
| R6-05 (major) | Fixed. (a) Table 8 has a new row "Solved among trials not refused (secondary)": 4/4 (100%; 40–100), 14/14 (77–100), 11/14 (79%; 49–95). There is a new bullet in 7.3: the aligned solve deficit is accounted for by refusal (Fisher p = 1.0 for both contrasts; Heretic vs abliterated p = 0.22), and the 4-trial estimate is very imprecise. (b) A one-line bullet says any refusal equals refused, because refused_after_engaging = 0. (c) Table 8 has a new row for cut-off before the first terminal command (0/0/0), and there is an "Endings" bullet (aligned 10 without a verified flag and 4 verified; abliterated 14 verified; Heretic 11 verified, 2 time cap, 1 submission limit). (d) A new 7.2 bullet covers the secondary Heretic vs abliterated contrasts: full refusal 0 vs 0, p = 1.0; any refusal 6 vs 2 discordant, p = 0.29; score +0.099, p = 9.6 × 10⁻¹⁰. (e) The Table 7 any-refusal row now has exact CIs: 91.5–96.8, 0.5–3.7, 1.3–5.4. | Tables 7 and 8; 7.2; 7.3 | All values come from `f1_summary.json` / `f2_summary.json`. The any-refusal CIs are Clopper-Pearson (`analyze_f.py:188`), so they fit Table 7's "exact" note. |
| R6-06 | Fixed. 4.1 now reports what the F1 provenance recorded: the same template and tokenizer hashes and the same think-end id in every arm, and a benign probe (one user message, no system prompt, no tools) that rendered identically in all arms (same SHA-256, 59 tokens). It says that whether the template changes prompts with system messages, tools or tool results was not checked, and it softens "differ in prompt formatting" to "may differ". The source is named. | 4.1 "Template and tokenizer differences"; 9 template bullet | From the private provenance files, via `f_derived_aggregates.json`. |
| R6-07 | Fixed. The abstract states the rule as "the trajectory ended on a text-only reply after zero terminal commands", says hand labels were pending, and no longer says "ended with no terminal command". 8.1 now says "refused ... by the pre-registered rule (a text-only reply after zero terminal commands; hand labels pending)", with no "declined". Contribution 4 adds "(by the pre-registered rule; hand labels pending)". The Table 10 limit cell adds "F2 refusal is by the pre-registered rule, hand labels pending". The 7.3 "Hand labels pending" paragraph and the 9 bullet now say "ended on a reply with no tool call, after zero terminal commands". | Abstract; 1.2 item 4; 8.1; Table 10; 7.3; 9 | 13 already said "refusals by the pre-registered rule; hand labels pending", and I added "by the pre-registered rule" to the new willing-to-attack sentence. |
| R6-08 | Verified from the private structured fields and sourced in the paper. 7.3 Aligned: "Its 10 rule-scored refusals each consisted of a single text-only reply with no tool call at all (from the private trial rows; `f_derived_aggregates.json`)". 7.3 Uncensored: the Heretic miss breakdown is now sourced, and "attempted every trial" is replaced by "ran terminal commands in every trial", which is supported by zero_terminal_calls = 0. 7.2, 9 and the notes: "every no-answer prompt was length-capped with its thinking still open", sourced. I also added "Whether that unfinished thinking contained refusals is unknown" (R6-11). | 7.2; 7.3; 9 "F1 answer truncation"; `F-EXECUTION-NOTES.md` F1 | Only aggregate facts are reported. No trace text was read. |
| R6-09 | Fixed. "For RQ4 the protocol states an expectation ... (score means the StrongREJECT score). For RQ5 it pre-specifies tests only, with no stated expectation." | 1.1 Hypotheses | |
| R6-10 | Fixed. 8.2 ¶1 now reads "On these 7 sandboxed tasks, chosen because every arm could solve them, a request that stated its criminal purpose plainly led to a verified attack in 25 of 28 uncensored trials and in 4 of 14 aligned trials". "These implications are tentative" is moved ahead of the two consequence bullets (with "and one criminal framing" added), and the old trailing paragraph is removed. The "not a safeguard" bullet becomes "do little against an attacker who can swap checkpoints", explicitly "follows from open weights rather than from our data", with F2 described as "consistent with it". | 8.2 | The selection caveat now sits in the sentence itself, so the trailing duplicate was dropped. |
| R6-11 | Fixed. Abstract: "The count was also 0 on the prompts both arms answered, against 51/74 and 74/111 for aligned." 7.2: "neither uncensored arm fully refused any prompt it answered, and on the prompts both arms answered the count was still 0 against 51/74 and 74/111 for aligned". "So the treatment worked" is removed from the abstract. | Abstract; 7.2 last ¶ | Table 10 keeps "0/313", and its limit cell already states the empty answers. |
| R6-12 | Fixed. The bullet is now titled "Weak refusal measure (v2)" and starts "In v2, ...". | 9 | |
| R6-13 | Fixed. (a) The 7.1 system-prompt item now says it drops v2's instruction to stay within the assigned environment and use the official description and starter files, and the 9 change list adds "which also drops v2's stay-in-scope instruction". (b) The 9 residual cues now say "`submit_flag` (also named in the user message)". | 7.1; 9 "F2 changes several things at once" | Checked against Appendix A.1 and `framing_f2._OBJECTIVE`. |
| R6-14 | Fixed. (a) Figure 6 is cited in 7.3 ("Figure 6 shows the v2, F1 and F2 results side by side") and in 8.1 (F2 bullet). (b) The panel title is now "F2: refused by rule (criminal framing)". (c) The fig6 arm labels are now capitalised (Aligned / Abliterated / Heretic). The `arm.capitalize()` call is used only inside `fig_willingness`, so fig1 to fig5 are unchanged. | `paper/make_figures.py:221, 234`; `fig6_willingness.svg`; 7.3; 8.1 | Regenerated. fig1 to fig5 are byte-identical (git shows no change). |
| R6-15 | Fixed. (a) The Appendix B "Stage F code" row now reads "all files listed in `stage_f/f_freeze.json`" and names all 14 code files. The results row adds `f_derived_aggregates.json`. (b) Appendix D row 6 now gives the finding count (18, R6-01 to R6-18; 5 major, 13 minor, plus one note), points to this report, and says verification is in `reviews/VERIFY-006.md`, which the verifier writes next. | Appendix B; Appendix D | |
| R6-16 | Checked and recorded; nothing moved and the sheet was not opened. The folder is not under any OneDrive account folder registered in the user's OneDrive registry keys (personal or work/school), and not under the `OneDrive` environment paths. It has no cloud-file attributes. Desktop and Documents are redirected into OneDrive, but the folder lies under neither. Windows File History is not configured. Other backup software was not checked. The notes also add that the sheet and key are to be moved back into the root-only directory, or deleted, after labelling. Section 10 now says the folder was checked not to lie inside any cloud-synced folder. | `F-EXECUTION-NOTES.md` "Hand-label sheet"; paper 10 "Harmful text" | No path or user name is written in any repository file. |
| R6-17 | Disclosed only, as required. `F-PROTOCOL.md` is unchanged, because it is frozen. The notes now have a line saying the status line is stale and that `16b6913` is the freeze. | `F-EXECUTION-NOTES.md` header | The freeze check verifies. |
| R6-18 | Fixed. I rewrote the abstract into: setting and confound; capability (v2); willingness (F1, F2); one sentence on stage C; and a closing "Taken together" sentence. It is now about 400 words (was about 610) and ends on its conclusion. | Abstract | Section 7 was not shortened. The reviewer said it reads well, and the new secondary outputs add about 150 words. |
| R6-19 (note) | No action. | – | I re-checked every new number against the JSON files. |

## Not done / deferred

- **Hand labels:** still pending (author task). Nothing in this cycle depends on them.
- **Other backup software (R6-16):** only OneDrive and Windows File History were checked.
- **Template effects beyond the benign probe (R6-06):** no stage F file records how prompts with system
  messages, tools or tool results render, so this is disclosed, not measured.
