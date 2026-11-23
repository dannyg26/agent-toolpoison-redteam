# Repair 008: supervisor feedback (review cycle 8)

**Source:** the supervisor's written feedback on the capstone update (2026-11-23), four points. This is the
only human review in the trail (paper Appendix D). Builder: Claude (AI). Nothing was committed, pushed or
run on a GPU. No frozen file was edited.

| Point | Feedback (summarised) | Status |
|---|---|---|
| S8-1 | Explain how truncated outputs in Study 3 are scored; report StrongREJECT scores, not just refusals | addressed |
| S8-2 | The criminal-framing trials (7 × 2) are not independent; note that next to the p-value | addressed |
| S8-3 | 9 vs 8 of 14 is no detectable difference, not equivalence; soften the claim and add CIs | addressed |
| S8-4 | Do not post raw harmful outputs in the public repository | addressed (none were posted; now stated) |

## S8-1: truncation scoring and StrongREJECT scores

**Changed**
- **Abstract.** Added the scoring rule in plain words (4,096-token limit including thinking; answer = text after
  thinking closes; if thinking never closed the answer is empty, classed "no answer" and scored 0; 3 / 189 /
  148 such answers). Added the three mean StrongREJECT scores with bootstrap CIs (0.071 [0.055–0.088], 0.227
  [0.195–0.261], 0.326 [0.289–0.364]) and the Wilcoxon results (p = 0.003 and p < 10⁻¹²), plus the post hoc
  answered-only means (0.071, 0.574, 0.619†).
- **§7.1.** New paragraph and table, "How truncated outputs are scored (frozen rule)", covering the three cases
  (finished; closed but length-capped, so the partial answer is judged; never closed, so `no_answer` and 0) and
  stating that `no_answer` never counts as a refusal.
- **§7.2.** New Table 7b† (all prompts / answered / answered and not length-capped, per arm, with CIs and n)
  and paired answered-only contrasts. Text notes that the answered subsets are selected by whether thinking
  finished.
- **§8.1** F1 bullet, **§9** "F1 answer truncation", **§8.4 Table 10**, **§13 Conclusion** and the **README**
  now carry the scores and the scoring rule.

**New post hoc numbers.** These come from `paper/posthoc_f1_scores.py`, run in WSL as root on the private
session `/home/capstone-study/stage_f/private/f1a`, with output `paper/f1_score_sensitivity.json` (aggregates
only, no model text).
- The script loads rows exactly as the frozen `analyze_f.py f1` does: it imports the frozen rule,
  `finish_reason == 'length'`, the judge field and the bootstrap settings.
- **Checks:** it reproduced the frozen all-prompt means exactly (0.0705 / 0.2274 / 0.3264), and every
  `no_answer` prompt had score 0 (0 non-zero of 3 / 189 / 148).

**Results:**

| Arm | Answered (n) | Answered and not capped (n) |
|---|---|---|
| Aligned | 0.071 (310) | 0.067 (305) |
| Abliterated | 0.574 (124) | 0.617 (74) |
| Heretic | 0.619 (165) | 0.660 (111) |

Paired differences on prompts answered in both arms:
- abliterated vs aligned: +0.508 (124 prompts);
- Heretic vs aligned: +0.556 (165 prompts);
- both p < 10⁻¹⁵.

The computed p was 0.0, a floating-point underflow, so the paper reports it as a bound.

## S8-2: F2 non-independence next to every p-value

**Changed**
- **Abstract:** the clustered test is now the headline ("aligned refused more often on all 7 tasks … sign-flip
  p = 0.016, the smallest possible with 7 tasks"). Fisher's p = 0.00015 follows, labelled as treating trials as
  independent and possibly overstating significance.
- **§7.1:** the design text now explains why the clustered test is the more appropriate one.
- **Table 9:**
  - the caption explains the 7 × 2 clustering;
  - clustered rows come first and Fisher rows are labelled "assumes independent trials";
  - a new post hoc† clustered solve row was added.
- **§7.3 secondary text:** an independence caveat on every Fisher p, plus the clustered p for Heretic vs
  abliterated solves.
- **Other places:** §8.1 F2 bullet, §8.2 (pointer to Table 9), §9 "F2 sample", §8.4 Table 10, §13,
  contributions item 4 and the README.

**New post hoc numbers.** These come from `paper/posthoc_f2_clustered.py`, with output
`paper/f2_solve_clustered.json`.
- **Method:** it uses the frozen `sign_flip_exact` on the per-task solve proportions in the released
  `f_derived_aggregates.json`.
- **Check:** it reproduces the frozen refusal result (p = 0.015625 for both contrasts).
- **Solves:**
  - abliterated vs aligned: 7/7 tasks differ, p = 0.016;
  - **Heretic vs aligned: 5/7, p = 0.0625;**
  - Heretic vs abliterated: p = 0.5.

**Disclosed consequence:** with the task as the unit, the Heretic-vs-aligned solve difference (Fisher
p = 0.021) is not significant at 0.05. This is stated in §7.3 and §9. The frozen protocol still names Fisher as
primary, so Fisher is kept and labelled rather than removed.

## S8-3: "no detectable difference, not equivalence", with CIs

**Changed.** Each of these now gives the per-arm exact CIs (35–87%, 29–82%), the paired Tango intervals (−31.5 to
+15.9, −35.4 to +21.6) and the plain reading "about two to three more tasks, or four to five fewer":
- the abstract (capability paragraph and the "Taken together" sentence);
- contributions item 2;
- §8.1 first paragraph, with the bold "No difference was detected, which is not the same as no difference";
- §13 Conclusion;
- the README.

**Softened wording:**

| Section | Before | After |
|---|---|---|
| §8.1 | "we found no sign that ablation reduced or increased competence" | "detected no change … but the intervals leave room for a change of several tasks in either direction" |
| §8.1 combined | "were not detectably more capable" | "No capability difference was detected" |
| §8.2 | "offers an attacker little beyond what the aligned model gives" | "we could not detect any added capability … a modest gain (about two to three of 14 tasks) remains compatible" |
| §8.2 bullet | "approximated what the uncensored variants could do" | "a reasonable first measure … should not be assumed to match an uncensored variant's capability exactly" |

**Also:** §8.4 Table 10 now says "no difference between arms was detected, which does not show equal capability".

The vague "most trials" phrasing was also replaced with the counts (10 of 14) in the abstract, contributions,
§8.1 and §13.

## S8-4: no raw harmful outputs in the public repository

**Verified before the repository was made public (2026-11-22).**
- **Scope:** all 83 commits on every branch and the tag.
- **Not found:**
  - RunPod keys or other tokens;
  - `adj/` paths, transcripts or traces;
  - free-text model outputs;
  - harmful-output phrases (keyword scan).
- **Long texts present:** only published prompt and judge templates (the Jailbreak-R1 attacker template, and the
  PAIR and StrongREJECT judge templates).
- **Old results files:** the gpt-oss tool-poisoning result files contain boolean flags only.

**Changed**
- **§10:** new bullet, "No raw harmful outputs in the public repository", stating the above and the rule for
  future additions.
- **§11:**
  - the stale "not publicly accessible … 404" sentence and the `[Author to decide … public.]` note are replaced
    by "made public on 2026-11-22", with a pointer to §10;
  - the cycle 8 post hoc files are listed as aggregates only.
- **§1.1:** the "remote was not publicly accessible" sentence is updated.
- **README:** a new bullet stating that no raw harmful outputs are in the repository.
- **The new cycle 8 files** contain counts, means, intervals and p-values only.

## Other edits

- **Paper status line and header:** now mention cycle 8, and name the new † source files.
- **Appendix B:** lists the new scripts and outputs.
- **Appendix D:** new cycle 8 row.
- **Left unchanged, as instructed:** the other `[Author …]` notes in §10 (ethics review) and §14 (AI-use
  wording).

## Freeze checks (after all edits)

| Check | Result |
|---|---|
| `stage_f/freeze_f.py check` (WSL, root) | "stage F freeze verifies" |
| `stage_e/freeze_v2.py check` (WSL, root) | "CTF v2 freeze verifies" |
| `reviews/check_freeze_delta.py` (WSL, root, stage D venv) | "freeze delta as documented … all other frozen hashes match" |
| `stage_b/followup_tools.py check` | "follow-up freeze matches" |
| `stage_b/heldout_tools.py check` | "held-out freeze matches" |

**Manifest coverage:** no freeze manifest names the README, the paper or `paper/`.

**Files changed:**
- modified: `paper/CAPSTONE-PAPER.md`, `README.md`;
- added: `paper/posthoc_f1_scores.py`, `paper/f1_score_sensitivity.json`, `paper/posthoc_f2_clustered.py`,
  `paper/f2_solve_clustered.json`, `reviews/REPAIR-008.md`.

## Repair of REVIEW-008

All 9 findings were fixed in `paper/CAPSTONE-PAPER.md` and `README.md`. No number changed except the
added Holm values. No frozen file was touched, nothing was committed or pushed, and no model text was read
or written.

| ID | What changed |
|---|---|
| R8-01 | **Holm values** for the clustered sign-flip tests were computed with the frozen `analyze_f.holm_two`: refusal 0.03125 for both contrasts; solves 0.03125 (abliterated) and 0.0625 (Heretic). **Where they now appear:** next to the raw p wherever the clustered p is a headline (abstract, §1.2 item 4, Table 9 with a Holm column and a caption note, §7.3 text and the "Task-clustered test" bullet, §8.1, Table 10, §9 "F2 sample", §13, README). **Wording:** "smallest possible with 7 tasks" is now attached only to the raw 0.016. |
| R8-02 | The abstract and §8.1 no longer call the clustered test the pre-registered appropriate test. They say it was pre-registered as a sensitivity check, that Fisher was the frozen primary, and that giving it most weight is a post hoc choice made after supervisor feedback. The same applies in §7.1, the Table 9 caption, §13 and the README. |
| R8-03 | The selection caveat ("a selected subset: prompts where thinking finished", post hoc †) was added wherever 0.574/0.619 appear: abstract, README, §8.1 and §13 (§9 already had it). In §7.2, "does not depend on how empty answers are scored" became "the direction … is the same whether empty answers are scored 0 or excluded; no other treatment was tried". New sentences: the all-prompt means are lower bounds at this limit, and the answered-only means are not estimates at a longer limit. |
| R8-04 | The §7.1 truncation paragraph was rewritten. (a) The fallback split *tries to recover* an answer from the think-end token or unmarked text, and recovered none. (b) The first sensitivity analysis excludes every length-capped or no-answer prompt, including capped answers whose thinking finished. (c) In the 313-denominator refusal rates a no-answer counts as not refused: abliterated's 0/313 includes 189 empty answers, and 0 of its 124 answers were full refusals. The table cell now reads "`no_answer` (not a refusal)". |
| R8-05 | §11 and §1.1 no longer claim the push order is publicly checkable. They now say readers can inspect the freeze commits, content, hashes and commit timestamps, that timestamps are set by the committer, that push times are not publicly verifiable, and that this is weaker than an external registry. |
| R8-06 | §10 now names what was scanned on 2026-11-22: `main` at `5e375a8`, `reasoning-safety-removal` at `92c1a4f`, `stage-c-ctf-prefreeze` at `e0da9ee`, and the tag `confirm-prereg-v1`. It adds that later commits (from `08cdf95`) change only the paper, the README, the post hoc aggregate files and `reviews/`, and are held to the same rule. "83 commits" was removed. |
| R8-07 | The abstract went from 597 to about 470 words (409 before cycle 8). The CIs, the scoring rule (one clause: empty, scored 0, counted as not refused), the non-independence note with the clustered p and Holm, and one Fisher mention were kept. The Wilcoxon p and the full-refusal sensitivity moved out; both are in §7.2. |
| R8-08 | In §13, the 29–82% CI now follows "8 of 14", not "every easy task". |
| R8-09 | The §4.1 F1 headline now notes that 189 and 148 uncensored answers were empty (counted as not refused; Section 7.1), and that the 124 and 165 answers given also had 0 full refusals. |

Appendix D's cycle 8 row now cites REVIEW-008 (9 findings, 0 major, 5 minor, 4 nit) and this section.

**Freeze checks after these edits:**

| Check | Result |
|---|---|
| `freeze_f.py check` (WSL, root) | "stage F freeze verifies" |
| `freeze_v2.py check` (WSL, root) | "CTF v2 freeze verifies" |
| `check_freeze_delta.py` (WSL, root, stage D venv) | "freeze delta as documented … all other frozen hashes match" |
| `followup_tools.py check` | "follow-up freeze matches" |
| `heldout_tools.py check` | "held-out freeze matches" |
