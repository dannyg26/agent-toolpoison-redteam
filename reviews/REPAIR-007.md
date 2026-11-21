# REPAIR-007: repairs after REVIEW-007 (cycle 7)

Repairer, cycle 7. I changed `paper/CAPSTONE-PAPER.md`, `paper/make_figures.py`, `README.md`,
`reviews/check_freeze_delta.py`, `stage_d/DEVIATIONS-AND-LIMITATIONS.md` and `stage_f/F-EXECUTION-NOTES.md`,
and wrote this report. No frozen file was edited. No reported number changed. Nothing is committed or
staged. There were no pods, cloud calls or API keys. The label-sheet folder was not opened.

**Verification baseline (after all edits):**
- `python3 -B freeze_f.py check` (WSL, root): **stage F freeze verifies**.
- `python3 -B freeze_v2.py check` (WSL, root): **CTF v2 freeze verifies**.
- `reviews/check_freeze_delta.py` (WSL, root, stage D venv): now **passes** ("freeze delta as documented:
  modified EXPANDED-STUDY-PLAN.md, score_run1.py, test_run1.py (repaired score_run1.py, test_run1.py;
  appended EXPANDED-STUDY-PLAN.md) … all other frozen hashes match"). It failed before this repair.
- `python paper/paired_ci.py` and `python paper/make_figures.py` exit 0. `git status --porcelain paper`
  shows only the edited paper and script, so `paired_ci.json` and all six SVGs are byte-identical.
- Cross-references: every "Section N", "Table N", appendix and D-number in the paper resolves (D-01 to
  D-31 exist). Figures 1 to 6 are now all cited in the body.
- Privacy grep over the changed files (`rpa_`, `csawctf{`, `flag{`, Windows user paths): no hits.

**For the builder: `stage_c/ctf_trial_results.json` must be force-added** (`git add -f`; `.gitignore`
`*_results.json` ignores it). I checked all 28 records. The only fields are `task_id`, `condition`, `phase`,
`status`, `solved`, `reason`, `final_text_class` (`None` or `empty`), integer counts, timings, `checkpoint`
and `revision`. The string values are task ids, conditions, phases, statuses, five ending reasons, two
model ids and two revision hashes. There are no flags, credentials or model text.

## Findings

| ID | Status | Change |
|---|---|---|
| R7-01 (minor) | Fixed once the builder force-adds the file | `stage_c/ctf_trial_results.json` checked clean (see above). §11 and Appendix B are correct once it is released, so I left them unchanged. Appendix D's cycle 7 row says the file is released with this cycle's commit. |
| R7-02 (minor) | Fixed (no frozen file edited) | `stage_d/DEVIATIONS-AND-LIMITATIONS.md`: new **D-31** discloses the `418edc1` append-only "Decision update" to the frozen `EXPANDED-STUDY-PLAN.md`. I verified that the version before `418edc1` matches its frozen hash and that the current file starts with those bytes (8,832 to 9,445 bytes). D-31 also explains why `check_freeze_delta.py` failed, and gives paper wording. The sentence at l.18–19 now says what the script checks and points to D-31. `reviews/check_freeze_delta.py` (in no freeze manifest) now checks that each repaired file's `97f850f^` blob matches its frozen hash and that the working file equals its `97f850f` blob. It accepts `EXPANDED-STUDY-PLAN.md` only as an append to its `418edc1^` frozen version. It passes. Paper Appendix B now reads "D-01 to D-31". |
| R7-03 (minor) | Fixed (disclosed; protocol frozen) | Paper §7.3 "Hand labels pending": the sheet also shows how each trial ended. For 13 of 42 trials that identifies the arm (aligned-only text-reply endings, Heretic-only time or submission-limit endings), and it is a proxy for the rule outcome, so label–rule agreement will be optimistic. §9 "F2 refusal is a rule" bullet: the same statement. `stage_f/F-EXECUTION-NOTES.md`: a new bullet with the counts (10 and 3, from `f2_summary.json` descriptive ending reasons, which I re-checked). It notes that this is not a deviation and must be stated when labels are reported. |
| R7-04 (minor) | Fixed | §5.6: "about 12–19% faster with one in flight and 3–12% faster with two". The last sentence adds "(about 12%: that trial never ran with only one in flight)". I checked this against `posthoc_v2.json`: Heretic unlimited_subway `min_in_flight` 2, 2-in-flight speed-up +12.4/+3.3/+11.7%. §9 "Concurrency tail" now says "up to 12–19%". |
| R7-05 (minor) | Fixed | §3.3 is now scoped to "capability or attack success (stage B and v2)". It adds: "Stage F, which measured willingness rather than capability, did find large differences (Section 7)." |
| R7-06 (minor) | Fixed | §8.1 F1 bullet adds "(also none among the prompts answered within the token limit: 0 against aligned's 51/74 and 74/111)". §13 adds "(also none among the prompts they answered within the token limit)". |
| R7-07 (minor) | Fixed | `README.md` gets a new top block. It links the paper and gives the three checkpoints. CTF v2: 9/8/8 of 14, McNemar p = 1.0, results and protocol links, $9.87. Stage F: F1 181/0/0 full refusals with the empty-answer caveat, F2 10/0/0 refused (rule; hand labels pending) and 4/14/11 solved, links to both summaries, the protocol and the notes, $5.47. It also links the deviations file and `reviews/`. The stage C entry is marked "superseded by CTF v2" with the D-26 missing-address reason. The rest of the README is unchanged. |
| R7-08 (nit) | Fixed | §5.1 "Solve validity" adds "(in one Heretic trial split across two `xxd` lines)". |
| R7-09 (nit) | Fixed | Table 10 Evidence cell: "revisions in `v2_config.json`". I found no released file that records repository dates. |
| R7-10 (nit) | Fixed | §5.2 adds "(Figure 3)" after the interval sentence. §5.3 adds "; Figure 4" to the 9/10, 8/8, 8/8 sentence after Table 5. |
| R7-11 (nit) | Fixed | §1.2 item 4: "removes the CTF cues from the fixed text (including the official task description)". |
| R7-12 (nit) | Fixed | The "Endings" bullet in §7.3 moved, unchanged, from "Other pre-registered secondary outputs (raw p)" to the top of "Descriptive details". |
| R7-13 (nit) | Fixed | The header now says that numbers from `f_derived_aggregates.json` are also post hoc. They are not marked † but are always cited by that file name. |
| R7-14 (nit) | Fixed | §7.1: "Wilcoxon signed-rank test on the score (normal approximation, as frozen)". §7.2: "(Wilcoxon, normal approximation, p = 0.003, …)". |
| R7-15 (nit) | Fixed | `paper/make_figures.py` fallback message: "for figure 3". |
| R7-16 (nit) | Fixed | §9 "Deviations": "because that folder was root-only inside WSL and not convenient for the author to open". |
| R7-17 (nit, process) | Fixed | The header status reads "revised in review cycle 7". Appendix D has a cycle 7 row: 17 findings (R7-01 to R7-17; 0 major, 7 minor, 10 nit). 16 are fixed in the paper, README, deviations file and two scripts. R7-01 is resolved by releasing `stage_c/ctf_trial_results.json` with this cycle's commit. The verifier should adjust the row if verification changes it. |

## Summary

17 of 17 addressed. 16 are fixed in place. R7-01 is fixed once the builder runs
`git add -f stage_c/ctf_trial_results.json`. No result number, CI, p value, cost or hash changed. All
freeze checks pass, and the freeze-delta check now passes too.
