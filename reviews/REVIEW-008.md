# REVIEW-008: check of the cycle 8 repairs (supervisor feedback S8-1 to S8-4)

Reviewer (checker), cycle 8. Scope: the uncommitted changes on top of `08cdf95`. These are
`paper/CAPSTONE-PAPER.md` and `README.md` (modified), and `paper/posthoc_f1_scores.py`,
`paper/f1_score_sensitivity.json`, `paper/posthoc_f2_clustered.py`, `paper/f2_solve_clustered.json` and
`reviews/REPAIR-008.md` (new). I checked each of them against the four supervisor points and the released
results files. I did not rely on REPAIR-008's account.

Rules followed:
- no cloud, pod, key or spend; no commit, push or `git add`; `~/.runpod*` untouched;
- private F1 data not opened: `posthoc_f1_scores.py` was checked by reading its code, and its output against
  the frozen `f1_summary.json`;
- no model text, attack text or flag read or copied;
- the only file written is this one.

## What I ran

| Check | Result |
|---|---|
| `git diff --name-only` + untracked files vs `stage_e/v2_freeze.json`, `stage_f/f_freeze.json`, `stage_c/ctf_freeze.json`, `stage_d/run1_freeze.json`, `stage_b/*_freeze.json` | none of the 7 changed or new files is named in any manifest |
| `freeze_f.py check` (WSL, root) | "stage F freeze verifies" |
| `freeze_v2.py check` (WSL, root) | "CTF v2 freeze verifies" |
| `reviews/check_freeze_delta.py` (WSL, root, stage D venv) | "freeze delta as documented … all other frozen hashes match" |
| `stage_b/followup_tools.py check`, `heldout_tools.py check` | "follow-up freeze matches", "held-out freeze matches" |
| `python paper/posthoc_f2_clustered.py` (Windows, released files only) | exit 0; output **identical** to `paper/f2_solve_clustered.json` (ignoring line endings) |
| Sign-flip p by hand | refusal, each contrast: 7 non-zero task differences, all one sign → 2/128 = 0.015625. Solves, abliterated vs aligned: per-task differences 1, 1, .5, 1, .5, .5, .5 → 0.015625. Heretic vs aligned: get_it and puffin differences are 0, leaving 5 positive differences → 2/32 = 0.0625. Heretic vs abliterated: −1 and −0.5 → 2/4 = 0.5. All match the JSON and Table 9. |
| Fisher by hand (`analyze_f.fisher_exact`) | 0/14 vs 10/14 and 14 vs 4: 0.000153; 11 vs 4: 0.0213; 11 vs 14: 0.222. All match. |
| `f1_score_sensitivity.json` vs `f1_summary.json` | all-prompt means and bootstrap CIs equal the frozen ones. Answered-n 310/124/165 = `thinking_closed`, and no-answer 3/189/148 = `no_answer`. Answered and not capped 305/74/111 = `excl_capped_or_no_answer.n`. All paper and README numbers (Table 7b, paired bullets, abstract, §8.1, §9, §13) match the JSON at the stated rounding. |
| Code review of `posthoc_f1_scores.py` | It imports the frozen `analyze_f` (rule, `finish_reason == 'length'`, judge field, bootstrap settings, Wilcoxon) and builds the same eligible set as the frozen sensitivity analysis. It prints only n, means, CIs and p. The answer text is used only by `classify_willingness`. The p = 0.0 values are floating-point underflow of the frozen normal-approximation formula (`1 − erf`), so true p is below about 2 × 10⁻¹⁶ and "p < 10⁻¹⁵" is a safe bound. |
| v2 CIs and intervals vs `ctf_v2_summary.json`, `paired_ci.json` | 35–87%, 29–82%; Tango −31.5/+15.9 and −35.4/+21.6 are correct. ×14 tasks, the upper bounds are +2.2/+3.0 tasks and the lower bounds −4.4/−5.0, so "about two to three more, or four to five fewer" is right. |
| Point 4 scan | All JSON blobs in the whole history (92 unique, every ref): the only string fields over 300 characters are the published attacker and judge templates and one command line. The flag-like strings in the tree are all placeholders or fixtures (`flag{x}`, `flag{fixture}`, format strings). There are no trace, transcript, label-sheet or raw-output files in history. The two new JSON files hold counts, means, CIs and p-values only. `gh repo view` shows the repository is now PUBLIC. |
| Wording sweep (paper + README) | Searched for: 9/14, 8/14, "same", "as well as", "approximat", "little beyond", "equival", "not detectably", "more capable", every Fisher p, and every F1 refusal headline. Findings below. |
| Tables and cross-references | every Markdown table in the paper and README has a constant column count. The cross-references Section 7.1, 7.2, 10, 11 and Table 7b/9 point to the right places. |

## What is fully addressed

- **S8-3:** done everywhere 9 vs 8 is stated. That covers the abstract, contributions, §5.2, §8.1, §8.2,
  Table 10, §13 and the README. §3.3's "pattern of non-detection" wording was already qualified. No
  equivalence wording remains.
- **S8-2:** every F2 Fisher p in the paper and README now has an independence note next to it, or is
  covered by the §7.3 "all Fisher p-values here share the independence caveat" sentence.
- **Heretic-vs-aligned solve result (clustered p = 0.0625):** reported consistently in Table 9, the §7.3
  text and §9. It is not called significant anywhere: neither the abstract, §8, §13 nor the README gives a
  solve p-value. No figure carries a p-value.
- **Post hoc labelling:** the new numbers are marked † or "post hoc" wherever they appear, including the
  README.
- **S8-4:** the statements in §10 and §11 hold up against my history scan, apart from R8-05 and R8-06.

## Findings

| ID | Severity | Location | Problem and evidence | Suggested fix |
|---|---|---|---|---|
| R8-01 | minor | Abstract l.50–52; §1.2 item 4 l.154; Table 9 l.810, 812; §7.3 l.851–852; §8.1 l.909–910; Table 10 l.976; §9 l.1033–1035; §13 l.1164; README l.24 | The paper now treats the clustered test as the appropriate test **for the two primary contrasts**, but reports it only as raw p. The protocol (`F-PROTOCOL.md` l.164–173) pre-registered it as a raw-p sensitivity check. The frozen primary test that it now outranks is Holm-adjusted, and Fisher's Holm value (0.0003) is still given next to it. Holm over the two primary contrasts gives clustered refusal **0.031** for each contrast, clustered solves 0.031 (abliterated) and 0.0625 (Heretic). This changes no conclusion, but it does change the stated p-values. Also, "the smallest value possible with 7 tasks" is true only of the raw value. | Wherever the clustered p is the headline, give "raw p = 0.016, Holm 0.031". Or say explicitly that the clustered p-values are raw, as pre-registered. Add the Holm values to Table 9 and keep "smallest possible" tied to the raw p. |
| R8-02 | minor | Abstract l.50–51 ("the pre-registered task-clustered test is the appropriate check"); §8.1 l.909–910 ("is the appropriate one") | §7.1 (l.710–712) is correct: the clustered test is "a pre-registered sensitivity check, and in this paper we treat it as the more appropriate test". The abstract and §8.1 drop that distinction. A reader of the abstract would take the clustered test as the pre-registered primary. It was pre-registered only as a sensitivity analysis, Fisher was the frozen primary, and putting the clustered test first is a cycle 8 (post-results) judgment. | Abstract: "…so we give most weight to the task-clustered test, pre-registered as a sensitivity check: aligned refused more often on all 7 tasks… Fisher's test, the frozen primary, treats the 14 trials as independent…". §8.1: same qualifier. |
| R8-03 | minor | Abstract l.42–44 ("Because empty answers score 0, these understate the uncensored arms: among answered prompts only, the means were 0.071, 0.574 and 0.619†"); README l.26–28 ("…scored 0, so among answered prompts only the means are…"); §8.1 l.904–905; §13 l.1160; §7.2 l.780 ("The score difference therefore does not depend on how empty answers are scored") | The answered-only means are presented as if they corrected the understatement. They describe a selected subset: the prompts on which thinking finished, which is 124 and 165 of 313. §7.2 l.751 says it is unknown whether the unfinished thinking contained refusals. The selection caveat appears only in §7.2 l.782–783 and §9. The all-prompt mean is a valid lower bound because 0 is the minimum score. The answered-only mean is not an estimate of the all-prompt mean at a longer limit, and it could be above or below it. "Does not depend on how empty answers are scored" is shown only for two treatments, scoring them 0 or dropping them. | Abstract and README: "…among answered prompts only (a selected subset: prompts where thinking finished) the means were…". §8.1 and §13: add the same short parenthesis. §7.2 l.780: "The direction of the score difference is the same whether empty answers are scored 0 or excluded." |
| R8-04 | minor | §7.1 l.673–676 (new scoring paragraph) | This paragraph answers S8-1, and three statements in it are inaccurate. (a) The fallback split does not "exclude these prompts". It re-derives an answer from the `</think>` token id, or from text with no think markup (`pod_f1.py` l.6–19), and here it recovered none (§7.2 l.746). (b) The first sensitivity analysis excludes the length-capped prompts with closed thinking as well (5/50/54), not only the no-answer prompts. (c) "does not count for or against refusal" is not right for the headline rates. A no-answer stays in the 313 denominator as a non-refusal, so 0/313 for abliterated includes 189 empty answers (0/124 answered). | "Two pre-registered sensitivity analyses address these prompts. One excludes every length-capped or no-answer prompt (full refusal among prompts answered without the cap in both arms). The other is a fallback split rule that tries to recover an answer from the think-end token, and it recovered none. In the headline refusal rates (denominator 313), a no-answer counts as not refused." |
| R8-05 | minor | §11 l.1103–1104 ("so the freeze commits and their push order can now be checked by any reader"); §1.1 l.130–131 | Making the repository public lets a reader see the freeze commits and their committer timestamps. Those timestamps are set locally and are not third-party evidence. Public git data does not show when a commit was pushed, and the remote was private at the time. The sentence it replaces was more careful ("the push timestamp can be checked only by readers given access"). | "…made public on 2026-11-22, so the freeze commits and their timestamps can be inspected by any reader. Commit timestamps are set by the committer, so this is weaker evidence than an external registry (see 'What pre-specified means')." Mention push records only if they were checked to be visible to the public. |
| R8-06 | nit | §10 l.1087–1088 ("every commit on every branch and tag (83 commits) was scanned"); REPAIR-008 | `git rev-list --all --count` is **84**. `08cdf95` (2026-11-22 18:04 −05:00, on `origin/stage-c-ctf-prefreeze`) is the 84th, so the scan presumably preceded it. A reader who counts will get 84, or 85 after this cycle's commit, and cannot tell which commits were covered. My own JSON-history scan found nothing that contradicts the claim. | Name the tip that was scanned ("83 commits, through `e0da9ee`"). Add that the later commits change only the paper, README and review files and were checked under the same rule. |
| R8-07 | nit | Abstract l.17–62 | The abstract grew from 411 to 597 words. The willingness paragraph alone now carries the token-limit rule, the no-answer counts, three means with CIs, two Wilcoxon p, the answered-only means, the full-refusal sensitivity, the outcome rule, the hand-label status, the independence explanation, the clustered p, Fisher p and Holm. It reads as a results section. | Keep in the abstract: one clause for the rule ("answers whose thinking did not finish within 4,096 tokens were empty and scored 0"), the three means, the clustered p (R8-01/02) and a single Fisher mention. Move the CIs, the full-refusal sensitivity and the Wilcoxon p to §7.2. |
| R8-08 | nit | §13 l.1150–1151 | "…including every easy task (exact 95% CI 29–82%)": placed here, the CI reads as belonging to the easy tasks. | Move it: "completed 8 of 14 (exact 95% CI 29–82%) CTF web and binary-exploitation objectives…, including every easy task." |
| R8-09 | nit | §4.1 l.306–307 | "F1 then found 181/313 full refusals for aligned and 0/313 for each uncensored arm" has no empty-answer qualifier. This is the same issue R7-06 fixed in §8.1 and §13, and it is the one remaining F1 refusal headline without the scoring note. | Add "(189 and 148 of the uncensored answers were empty, because thinking hit the token limit; Section 7.1)", or "0 of the 124 and 165 answers they gave". |

## Summary

**9 findings: 0 major, 5 minor, 4 nit.**

- No number, CI, p-value or count is wrong.
- The freezes verify, and no frozen file was touched.
- The clustered F2 script reproduces its JSON from released files, and the sign-flip and Fisher values are
  correct by hand.
- The point 4 claims hold.

The minor items are about how the new post hoc numbers are framed, plus three inaccurate sentences in the
new truncation paragraph:
- R8-01 and R8-02: the clustered test's raw-vs-Holm status, and the fact that it is a promoted sensitivity
  test;
- R8-03: the selection caveat on the answered-only means;
- R8-04: the inaccurate sentences in the new truncation paragraph;
- R8-05: the push-order verifiability claim.
