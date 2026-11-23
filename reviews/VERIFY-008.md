# VERIFY-008: independent verification of cycle 8 (supervisor points S8-1 to S8-4, REVIEW-008 repairs)

Verifier, cycle 8. Scope: the uncommitted tree on top of `08cdf95`. That is `paper/CAPSTONE-PAPER.md` and
`README.md` (modified), and `paper/posthoc_f1_scores.py`, `paper/f1_score_sensitivity.json`,
`paper/posthoc_f2_clustered.py`, `paper/f2_solve_clustered.json`, `reviews/REVIEW-008.md` and
`reviews/REPAIR-008.md` (new). I checked every finding against the current text at each named location,
grepped for other occurrences, and recomputed the numbers from the released results files. I did not
rely on REPAIR-008's account.

Rules followed:
- no cloud, pod, key or spend; no commit, push or `git add`; `~/.runpod*` untouched;
- private F1 data not opened: `posthoc_f1_scores.py` was checked by reading its code against the frozen
  `stage_f/analyze_f.py`;
- no model text, attack text or flag was read or copied. The flag-like strings in history are format
  placeholders and synthetic fixtures; none is reproduced here.

In the repository I wrote this file and made the three small fixes listed at the end. Scratch scripts
lived in the session temp directory.

## What I ran

| Check | Result |
|---|---|
| `git diff --name-only` + untracked vs all 7 manifests (`stage_b/{pilot,followup,heldout}_freeze.json`, `stage_c/ctf_freeze.json`, `stage_d/run1_freeze.json`, `stage_e/v2_freeze.json`, `stage_f/f_freeze.json`) | none of the 8 changed or new files is named in any manifest (path or basename match) |
| `freeze_f.py check` (WSL, root, `python3 -B`) | **"stage F freeze verifies"** |
| `freeze_v2.py check` (WSL, root, `python3 -B`) | **"CTF v2 freeze verifies"** |
| `stage_f/test_f.py` (WSL, root, `python3 -B -m unittest`) | 23 tests, OK |
| `reviews/check_freeze_delta.py` (WSL, root, stage D venv) | "freeze delta as documented … all other frozen hashes match" |
| `stage_b/followup_tools.py check`, `heldout_tools.py check` | "follow-up freeze matches", "held-out freeze matches" |
| Direct SHA-256 of `stage_c/ctf_freeze.json` (32 files) and `stage_b/pilot_freeze.json` (15 files) | all match, 0 mismatches |
| `python paper/posthoc_f2_clustered.py` (Windows) | exit 0; output **identical** to `paper/f2_solve_clustered.json` (ignoring line endings) |
| Sign-flip by hand (own enumeration over all sign assignments, from `f_derived_aggregates.json` and `f2_summary.json` per task) | refusal: 7 non-zero same-sign task differences for each contrast, 2/128 = 0.015625 (equals the frozen `refused_task_clustered`). Solves: abliterated vs aligned differences 1, 1, .5, 1, .5, .5, .5, so 2/128 = 0.015625; Heretic vs aligned 1, 0, .5, 1, 0, .5, .5 (get_it and puffin zero), five positive differences, so 2/32 = 0.0625; Heretic vs abliterated 0.5 |
| Holm (m = 2) by hand | refusal: both 0.015625, so 2 × 0.015625 = 0.03125 each (paper 0.031). Solves: 0.015625 → 0.03125; 0.0625 → max(0.03125, 0.0625) = 0.0625 |
| Fisher by hand | 0 vs 10 and 14 vs 4: 0.000153 (Holm 0.000305); 11 vs 4: 0.0213 (Holm 0.0213); 11 vs 14: 0.222. All match `f2_summary.json` and Table 9 |
| F1 numbers vs `f1_summary.json`, `f_derived_aggregates.json`, `f1_score_sensitivity.json` | Table 7, Table 7b, the paired bullets, abstract, §4.1, §7.1, §8.1, Table 10, §9, §13 and README all match at the stated rounding. Cross-checks: 313 − 3/189/148 = 310/124/165 closed; 3 + 5, 189 + 50, 148 + 54 = 8/239/202 capped; 310 − 5, 124 − 50, 165 − 54 = 305/74/111 = `excl_capped_or_no_answer.n` |
| v2 numbers vs `ctf_v2_summary.json`, `paper/figures/paired_ci.json` | 9/8/8; Clopper–Pearson 0.3514–0.8724, 0.2886–0.8234; Tango −0.3147/+0.1593, −0.3536/+0.2164; McNemar and Holm 1.0. × 14: +2.2/+3.0 and −4.4/−5.0 tasks, so "about two to three more, or four to five fewer" holds |
| Code review of `posthoc_f1_scores.py` | It imports the frozen `analyze_f` and uses its `_read_jsonl`, `classify_willingness`, `finish_reason == 'length'`, the `strongreject_score` field, `bootstrap_mean_ci` with the frozen resamples and seed, and `wilcoxon_signed_rank`. The "answered" set is `class != 'no_answer'`; "clean" adds `not length_capped`, the same eligibility as the frozen `full_refusal_excl_capped_or_no_answer`. It writes only n, means, CIs, p and two counts. Answer text goes only into `classify_willingness`. The `p = 0.0` values come from `1 − erf` underflow in the frozen normal approximation, so "p < 10⁻¹⁵" is a safe bound. |
| Branch tips named in §10 | `origin/main` 5e375a8, `origin/reasoning-safety-removal` 92c1a4f, `e0da9ee`, tag `confirm-prereg-v1`: 83 commits; the only commit outside them is `08cdf95`, which changes only `paper/CAPSTONE-PAPER.md` (3 deletions). So §10 is accurate. (Local `main` is at 7f0d5ec, an ancestor already covered.) |
| Point 4 scan | Changed and new files: no secrets, user paths, real flags or quoted model text. The only quoted strings in added lines are two section titles. History: 313 unique paths ever committed; none is a trace, transcript, `.jsonl`, label sheet or raw-output file. The only strings over 300 characters in the 74 tracked JSON files are the published attacker and judge templates, one command line and an `_about` note. The flag-like strings in history are format placeholders and one synthetic fixture. |
| Markdown tables (paper + README) | every table has a constant column count |
| Cross-references in added text | Sections 1.1 ("What pre-specified means here"), 7.1, 7.2, 10 and 11, Table 7b, Table 9 and Appendix A all point to the right content |
| Abstract length | **469 words** (409 at HEAD; 597 before the REVIEW-008 repair) |

## Verification table (REVIEW-008)

| Finding | Verdict | Evidence | Remaining |
|---|---|---|---|
| **R8-01** (minor) clustered p reported raw only | **VERIFIED** | The text now gives "raw p = 0.016 … Holm 0.031" in all these places: the abstract (l.44, †), §1.2 item 4, Table 9 (a Holm value in every clustered cell, plus a caption sentence on the post hoc Holm), the §7.3 text (l.823–824) and the "Task-clustered test" bullet (l.856–858), §8.1 (l.916), Table 10, §9 "F2 sample" (l.1040–1045, refusal and solves), §13 and the README (l.25). "Smallest possible/attainable" is tied to the raw value everywhere (grep: l.44, 815, 824, 857, 1041). Holm values match my hand computation. | 3 places did not mark the post hoc Holm with †; I added it (fixes 1–3) |
| **R8-02** (minor) clustered test presented as the pre-registered primary | **VERIFIED** | Abstract l.42–45: "we give most weight (a post hoc choice) to the task-clustered sign-flip test, pre-registered as a sensitivity check … Fisher's test, the frozen primary". The same wording is in §8.1 (l.915–918), §7.1 (l.709–711), the Table 9 caption (l.807–811), §13 and the README. No remaining "the appropriate" or "pre-registered … appropriate" wording (grep). This matches `F-PROTOCOL.md` l.161–173, where Fisher is primary and the clustered test is a raw-p sensitivity check. | none |
| **R8-03** (minor) answered-only means presented as a correction | **VERIFIED** | The selection caveat ("a selected subset: prompts where thinking finished", †/post hoc) sits next to 0.574/0.619 in the abstract (l.37–38), README (l.20), §8.1 (l.910–911), §13 (l.1174–1175) and §9 (l.998–999). §7.2 l.779–786 now reads "the direction … is the same whether empty answers are scored 0 (frozen) or excluded (post hoc); no other treatment was tried". It adds that the all-prompt means are lower bounds at this limit, that the answered-only means are not estimates at a longer limit, and that they "could be above or below". | none |
| **R8-04** (minor) three inaccurate sentences in the truncation paragraph | **VERIFIED** | §7.1 l.668–675 fixes all three. (a) The fallback "tries to recover an answer from the think-end token or from text with no think markup; it recovered none". This matches `pod_f1.py` l.10–19 and `f1_summary.json` `fallback_split`, whose counts are identical to the primary ones. (b) The first analysis "excludes every length-capped or no-answer prompt, including length-capped answers whose thinking did finish". This matches the frozen `eligible` in `analyze_f.py` l.222. (c) "In the headline refusal rates (denominator 313) it counts as not refused, so abliterated's 0/313 … include 189 empty answers (0 of its 124 answers …)". The scoring table cell reads "`no_answer` (not a refusal)". | none |
| **R8-05** (minor) push order claimed publicly checkable | **VERIFIED** | §11 l.1115–1119 and §1.1 l.120–123 now say that readers can inspect the freeze commits, content, hashes and commit timestamps. They add that timestamps are set by the committer, that push times are not publicly verifiable, and that this is weaker than an external registry. No other "push order" claim remains (grep "push"). | none |
| **R8-06** (nit) "83 commits" ambiguous | **VERIFIED** | §10 l.1096–1100 names the scanned tips (`main` 5e375a8, `reasoning-safety-removal` 92c1a4f, `stage-c-ctf-prefreeze` e0da9ee, tag `confirm-prereg-v1`) and says later commits from `08cdf95` change only paper, README, aggregates and `reviews/`. Checked with `git rev-list`: those tips cover exactly 83 commits, and the only commit outside them is `08cdf95`, which touches only the paper. "83 commits" no longer appears. | none |
| **R8-07** (nit) abstract too long | **VERIFIED** | 469 words (was 597). The Wilcoxon p values and the full-refusal sensitivity moved out of the abstract and are in §7.2 (l.733–740). The abstract keeps one scoring-rule clause, three means with CIs, the answered-only means with the caveat, the clustered p with Holm, and one Fisher mention. It is still 60 words longer than at HEAD, which is acceptable given the added content the supervisor asked for. | none |
| **R8-08** (nit) CI placement in §13 | **VERIFIED** | l.1164–1165: "completed 8 of 14 (exact 95% CI 29–82%) CTF web and binary-exploitation objectives …, including every easy task." | none |
| **R8-09** (nit) §4.1 F1 headline lacked the empty-answer note | **VERIFIED** | l.299–302: "Of the uncensored answers, 189 and 148 were empty because thinking hit the token limit, and they count as not refused (Section 7.1); among the 124 and 165 answers … there were also 0 full refusals." This is correct (`willingness_counts`). A grep of every "181" and "0/313" shows each F1 refusal headline now has the scoring note nearby. That covers the abstract, §4.1, §7.1, Table 7, §8.1, Table 10, §13 and the README. | none |

## Supervisor points

| Point | Verdict | Evidence |
|---|---|---|
| **S8-1** Explain truncation scoring in F1; report StrongREJECT scores, not just refusals | **MET** | The §7.1 "How truncated outputs are scored (frozen rule)" table covers all three cases (finished; closed but length-capped, partial text judged; never closed, `no_answer`, 0, not a refusal). It matches `pod_f1.py` and `F-PROTOCOL.md` l.37–51. The scoring rule is also stated in the abstract, §4.1, §8.1, Table 10, §9 and the README. Mean scores with bootstrap CIs (0.071/0.227/0.326) appear in the abstract, Table 7, Table 7b, §8.1, Table 10, §13 and the README. Both frozen Wilcoxon contrasts are in §7.2, and the post hoc answered-only means are labelled and caveated. Every number checks against the JSON files. |
| **S8-2** Note the 7 × 2 non-independence next to the p-value | **MET** | Every F2 p-value in the paper and README (grep "0.00015", "0.0003", "0.021", "0.22", "0.016", "0.0625", "Fisher") is either next to an explicit independence statement or under the §7.3 l.827–828 blanket caveat ("all Fisher p-values here share the independence caveat above"). The covered places are the abstract, §1.2, §7.1, Table 9 caption and rows, §7.3, §8.1, §8.2 (pointer to Table 9 next to 25/28), Table 10, §9, §13 and the README. A clustered solve test was added. It shows that the Heretic solve difference does not survive at the task level (0.0625), and this is disclosed in §7.3 and §9. |
| **S8-3** 9 vs 8 is "no detectable difference, not equivalence"; soften and add CIs | **MET** | A grep of every 9/14, 8/14, "9 vs 8", "8 of 14" and "8–9" shows each comparative statement now carries per-arm exact CIs and/or the paired Tango intervals, plus an explicit "not equivalence / does not show equal capability" statement. The places are the abstract, §1.2 item 2, Table 1, §5.2 and Table 4, §8.1, §8.2, Table 10, §13 and the README. A sweep for "equival", "same capab", "approximat", "little beyond", "not detectably", "no sign that", "unchanged" and "preserv" finds no equivalence claim. The remaining hits are negations, the protocol quote, the Arditi citation and the stage B "not equivalence" README entry. The §4.1 RQ1 sentence (l.416) is descriptive and sits under Table 1 with its CIs. |
| **S8-4** No raw harmful outputs in the public repo | **MET** | The changed and new files contain only counts, means, CIs and p-values. My history path scan and tracked-JSON long-string scan agree with §10 and with REVIEW-008: no traces, transcripts, label sheets, forbidden-prompt answers, exploit commands or real flags. The policy is now stated in §10, §11 and the README. |

## New issues found

1. **Nit, not fixed (wording judgment).** Appendix D's introduction (l.1375–1377: "These were separate
   AI-agent review cycles …, not human or external review") and §14 (l.1199–1201: "every role was played
   by an AI agent …, not by human reviewers") now contradict the new cycle 8 row, which calls the
   supervisor's feedback "the only human review in this trail".
   - Suggested fix: add "except the supervisor's written feedback in cycle 8" to both sentences.
2. **Nit, not fixed.** The README (l.25) gives "Holm 0.031" for the clustered test without marking it as
   post hoc. The test itself is labelled "pre-registered as a sensitivity check", which was raw-p only.
   - Suggested fix: "raw p = 0.016 (Holm 0.031, computed post hoc)".
3. **Nit, not fixed.** The paper's header Date is still 2026-11-20, although the status line says it was
   revised in cycle 8 (2026-11-23).
4. **Cosmetic, not fixed.** Some repaired source lines are much longer than the surrounding ~110-character
   wrap (l.26, l.141–143, l.1179–1181). The rendered output is unaffected.

None of these changes a number or a conclusion. No contradiction between the abstract, body, conclusion and
README was found on any number. No new overclaiming was found, and every new sentence parses.

## Fixes applied by the verifier

All three apply the paper's own convention (header, l.12–13: numbers computed for this paper are marked †)
to the post hoc Holm value of the clustered refusal test, which REPAIR-008 added:

1. `paper/CAPSTONE-PAPER.md` §1.2 item 4: "(Holm 0.031)" → "(Holm 0.031†)".
2. `paper/CAPSTONE-PAPER.md` Table 10, "Uncensored model" evidence cell: "Holm 0.031)" → "Holm 0.031†)".
3. `paper/CAPSTONE-PAPER.md` §13: "raw p = 0.016, Holm 0.031)" → "raw p = 0.016, Holm 0.031†)".

No frozen file was edited. No manifest names the paper, the README, `paper/` scripts or `reviews/`.
The freeze checks above were run before these fixes, and the fixes touch only the paper.

## Summary

- 9 of 9 REVIEW-008 findings **verified** (0 partly fixed, 0 not fixed).
- All 4 supervisor points **met**.
- 0 substantive new issues; 4 nits/cosmetic items listed; 3 small verifier fixes (†).
- All freezes verify, the F2 clustered script reproduces its JSON, and every recomputed p, Holm value,
  F1 number and v2 interval matches the paper and README.

The tree is ready to commit: add the four `paper/` files and `reviews/REVIEW-008.md`, `REPAIR-008.md` and
`VERIFY-008.md`. Optionally fix new issue 1 first.
