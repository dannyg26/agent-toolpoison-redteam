# VERIFY-004: verification of `paper/CAPSTONE-PAPER.md` against REVIEW-004 / REPAIR-004 (cycle 4)

Verifier role, 2026-11-20. Read-only except this file. No model or cloud call, no git write. Checks were done
against the text, by recomputation and by re-running the paper scripts in a scratch copy of the repository
(`paired_ci.py` writes into `paper/figures/`, so it was not run in place).

## What was run or recomputed

- **`paper/paired_ci.py` and `paper/make_figures.py`**, re-run in a scratch tree that holds copies of the
  inputs (`stage_b/analyze_heldout.py`, `heldout_tools.py`, `ctf_v2_summary.json`, `posthoc_v2.json`,
  `stage_c/ctf_trial_results.json`):
  - All six outputs (`paired_ci.json` and the 5 SVGs) are **byte-identical** to the committed
    `paper/figures/*`.
  - All internal asserts pass: the grid equals the frozen `solved_tasks`, and the totals are
    [2, 1, 9, 8, 8].
  - All 5 SVGs parse as well-formed XML (`xml.dom.minidom`).
- **The Tango code is unchanged.** `paired_ci.py` imports `tango_ci`, `wilson`, `mcnemar_exact` and `Z`
  directly from `stage_b/analyze_heldout.py`; there is no copy. `stage_b/` has no working-tree changes
  (`git status`), and its last commit is `6130230` (the stage B freeze).
- **Independent interval check:**
  - A separate brute-force grid over the Tango score statistic (step 1e-5) reproduces every Tango limit
    to 4 dp: (8,0,1,5) → −0.3147/0.1593; (7,1,2,4) → −0.3536/0.2164; (7,1,1,5) → ±0.2655.
  - Newcombe method 10 on Newcombe's 1998 worked example (36,12,2,0) gives 0.0569–0.3404, the published
    values. Tango on the same data gives 0.0611–0.3447, which agrees with the grid search.
  - Paper rounding in Table 4 and the abstract is correct. The statement "up to about two or three more
    … or four to five fewer" matches 14 × the limits (2.2–3.0; 4.4–5.0).
- **Figures' embedded data:**
  - Fig. 2 has 14 rows × 5 columns. Its stage C cells match `ctf_trial_results.json` (aligned: 2 solved,
    3 call limit, 3 context, 4 time, 2 ended; abliterated: 1, 2, 4, 6, 1) and Table 6. Its v2 cells match
    Table 2. Totals: 2/14, 1/14, 9/14, 8/14, 8/14.
  - Fig. 4 shows 9/4/1, 8/6 and 8/6.
  - Fig. 5 shows 2→9, 1→8, and heretic "not run".
  - Fig. 3 line endpoints map back exactly to the `paired_ci.json` limits (px = 200 + (v + 0.5)·360).
- **Appendix A vs code:** a script parsed the constants with `ast`. `SYSTEM`, `TOOLS` (JSON-equal),
  `CUTOFF_NOTICE`, `ELIDED`, `INVALID_COMMAND`, `stage_c` `UNPARSED_CALL_NOTICE` and the `task_prompt`
  target sentence (web and pwn variants, `<host>`/`<port>` substituted) all **match exactly**.
- **Word count:** `wc -w` = 9,648; Abstract to References excluding table rows = 7,464. This matches the
  repair's "about 7,500 / 9,600".
- **Repository visibility:** anonymous `api.github.com/repos/…` returns 404. `git branch -r --contains 8f759f2`
  → `origin/stage-c-ctf-prefreeze`. Both as stated in §10.
- **Citations (web, read-only):**
  - Verified: EnIGMA 2409.16165; AgentHarm 2410.09024; CyberSecEval 3 2408.01605; Jailbreak Tax
    2504.10694 (authors, title, "up to 92%"); CTFTiny 2508.05674 (Shao, Rani, Milner, Xi; 50 challenges);
    InjecAgent 2403.02691 (full title with "Large Language Model"); Qi et al. 2310.03693; NYU CTF Bench
    2406.05590; InterCode-CTF (Yang, Prabhakar, Yao, Pei, Narasimhan; NeurIPS 2023 MASEC; 100 picoCTF
    tasks); UK/US AISI page (19 Nov 2024; 40 and 47 challenges); Heretic BibTeX (Weidmann, 2025, exact
    title); CTFTiny licence GPL-2.0; Tango 1998, Stat Med 17(8):891–908.
  - No fabricated reference was found.

## Findings

| ID | Claimed action | Verdict | Evidence | Remaining |
|---|---|---|---|---|
| R4-01 | Causal harness language removed; results-file wording used | **PARTIAL** | Abstract l.43–45, §6 l.574–580 and §7.3 l.626 now say "coincides", "not a causal test", "cannot attribute it causally". The repair's grep targets are gone. **But** §2 l.132–134 still says: "Our stage C to v2 comparison adds a cautionary example: an omitted target address and unreadable binary output **were enough to depress measured capability to near zero**." That is a causal claim. Also, §7.3 l.625–626 ("far larger than any difference between checkpoints") and §12 l.763–765 ("changed far more between two harnesses … than between checkpoints") bring back the harness-vs-refusal-removal comparison the reviewer asked to drop. §12 also calls it a change "between two harnesses", although budget changed too. | Rewrite §2 l.132–134 (e.g. "…adds a cautionary example: measured capability was near zero under a harness later found to omit the target address and show raw binary output; the change is not a causal estimate"). Rephrase or caveat the "far more/far larger" comparisons, and say "between two runs that differed in harness and budget". |
| R4-02 | Per-arm 2→9, 1→8; heretic absent from stage C | VERIFIED | No "1–2" left. "8–9" appears only in Table 7 (v2 arms). Abstract, §1.2, §6, §7.3 and §12 give per-arm numbers. Fig. 2 and Fig. 5 mark heretic "not run". Stage C solves (control: poem_collection, shreeramquest; main: poem_collection) checked in `ctf_trial_results.json`. | — |
| R4-03 | Non-detection rephrased; paired-difference CIs added | VERIFIED | "most likely" and "no detectable gain" are absent. "does not add capability" appears only as one horn of an undistinguishable alternative (§8 l.660). §5.2, §7.1 and §12 use the required wording. CIs recomputed and confirmed (see above). The method and post hoc status are stated in §4.7. | — |
| R4-04 | Manipulation-check disclosure | VERIFIED | §4.1 l.239–262 is accurate against `REFUSAL-AUDIT.md` and `refusal_audit_counts.json`: 0/32 first attempts per model held-out, 0/10 per model pilot, authorisation framing, post hoc pattern endpoint, aligned not refusing either. The same revisions (`37561816`, `739e3c5`) are confirmed in `HELDOUT-RESULTS.md` l.197. Stage D aligned-only matches D-03/D-04. The statement is prominent: Abstract l.38–39, §3.2, §4.1, §7.2 l.621, Table 7, §8 first limitation, §12 l.763. | Minor: §7.1 l.604 "because there was nothing to unlock" is firmer than the evidence (a pattern scan); "no refusal was observed to unlock" would be exact. |
| R4-05 | AI-use disclosure; "independent" dropped | VERIFIED | §13 is present and marked **[Author to confirm wording per course policy]**. Appendix D says "separate AI-agent review cycles … not human or external review". `independent` appears only at l.237 ("not independent ones") and in the verbatim tool description (l.857). | The author must fill in the policy citation (placeholder l.785). |
| R4-06 | Verbatim steering texts appendix | VERIFIED | Programmatic exact match for all texts (see above). No flag or task-specific content. The CTF framing is noted in §3.1 and §8. | — |
| R4-07 | Full paper; tables and figures | VERIFIED | Tables 2–7 and Figs 1–5 are present. Table 2 matches results l.58–73; Table 3 matches l.81–85; Table 5 matches the results endings table and `ctf_v2_summary.json`; Table 6 matches `ctf_results_summary.json`. About 7.5k words of main text. The wall-time figure was not made (disclosed; the split is in §5.3). | Optional. Cosmetic script bug: `make_figures.py` l.235 says "for figure 5"; it means Fig. 3. |
| R4-08 | Related work rewritten with six strands | PARTIAL | All added references verified (see above). However, §2 l.128 says "Several studies show that the agent harness matters **as much as** the model". None of the cited works establishes parity, so this generalisation is unsupported. See also the R4-01 residual at l.132–134. | Soften to "Several studies show that the agent harness can change measured capability substantially". |
| R4-09 | RQ1–RQ3 and hypotheses | VERIFIED | §1.1 matches V2-PROTOCOL l.9–12 and l.118/124 (quotes exact). RQ2 is two-sided. | — |
| R4-10 | Requirement-mapping table with caveats | VERIFIED | Table 7 carries "recent, not newest", "repository date ≠ cutoff", "harness supplies …" and the publisher-label caveat. | — |
| R4-11 | Project context subsection | VERIFIED | §3.3 matches the sources: 0.52 vs 0.00 (`STUDY-RESULTS.md` l.15, non-blatant, reasoning off); −0.533/−0.300 (`RESULTS.md` l.70–71); stage A (`RUN-LOG.md` l.84–107); 17/32 vs 16/32, +3.1, Tango −16.5 to +22.7, p = 1.00, 11/12 (`HELDOUT-RESULTS.md`). | — |
| R4-12 | Token-cap mechanism across stages | VERIFIED | §6 l.582–589: 1,490/5,146 (29%) and 1,593 (D-07); empty endings at 4,096 (D-22); 79% (D-23); 82–83% (D-30). | Minor: the 79% figure is D-23, not D-22; it could be cited. |
| R4-13 | Limitations (a)–(h) | VERIFIED | Present in §8 (and §5.6): concurrency tail, context assumption, weak refusal measure, stale shell, template not diffed, not blind (D-25), not comparable (D-26), no human baseline. Figures match results l.149–167 and D-29/D-30. | — |
| R4-14 | "Pre-specified" defined | VERIFIED | Title and §1.1 l.97–101 (pushed commit, not a registry, not public, written after stage C). | — |
| R4-15 | Code and data availability | VERIFIED | §10: URL, commit, branch and 404 status confirmed. Released and withheld items and non-reproducibility are stated. | The author decides on public release (placeholder). |
| R4-16 | Method descriptions | VERIFIED | "hand-tuned" is gone; the card wording is used; "two different … not independent". | — |
| R4-17 | CTFTiny, Heretic, InjecAgent references; model cards | VERIFIED | All three were fixed and verified on the web. Model cards and vLLM were added with access dates. Tango was confirmed. Newcombe 1998 (Stat Med 17(22):2635–2650) was not web-confirmed in this cycle, but it is the standard citation, and its worked example reproduces. | Optional: confirm the Newcombe page range. |
| R4-18 | Ethics expanded | VERIFIED | §9: no human subjects (author placeholder); GPL-2.0 confirmed; dual use; withheld traces; $9.87 quoted; $3.71, $2.07 (`HELDOUT-RESULTS.md` l.267–272, settled $2.0675) and $1.52 (README l.34). | — |
| R4-19 | Sampling-model sentence | VERIFIED | §4.7 l.343–344. | — |
| R4-20 | Refusal-method limit in the abstract | VERIFIED | Abstract l.37–38; §5.4 l.496–497. 806 = 237 + 266 + 303; 217 = 106 + 111. | — |
| R4-21 | 4 of aligned's 5 | VERIFIED | §5.3 l.466–467. | — |
| R4-22 | 36.0–36.7 tok/s | VERIFIED | l.473. | — |
| R4-23 | 8,192 characters | VERIFIED | l.317–318, matching V2-PROTOCOL l.35–36 and `DISPLAY_LIMIT, HEAD, TAIL = 8192, 6144, 2048`. | — |
| R4-24 | Minimums clause | VERIFIED | l.437–438. | — |
| R4-25 | "jointly minimising" | VERIFIED | §2 l.147–148; §4.1. The current (2.x) README describes TPE/Optuna with configurable refusal and KL scorers. It does not explicitly confirm co-minimisation for v1.4.0, but nothing contradicts it. | — |
| R4-26 | Request-time clause | VERIFIED | §6 l.566–567. Stage C control (aligned) median 6.7 s (`CTF-RESULTS.md` l.75); v2 11.4 s. | — |
| R4-27 | Title block; reviewer notes removed | PARTIAL | The title block is present and the draft note is removed. Appendix D row 4 still reads "verification pending". | Update row 4 to its final status (e.g. "verified in VERIFY-004; 2 partial items repaired"). Fill the author placeholders before submission. |
| R4-28 | Title | VERIFIED | l.1. | — |
| R4-29 | Threat model additions | VERIFIED | §3.1 l.172–181. | Minor: §7.3 l.639–641 "an adversary **can** improve a model's offensive performance by engineering its harness" is an unhedged general claim. Use "may be able to". |

### Numbers check (item 1)

These numbers match ground truth:

- **Solves and paired results:** 9/8/8; CIs 35–87% and 29–82%; web 3/3/3; pwn 6/5/5; paired 8/0/1/5,
  7/1/2/4 and 7/1/1/5; p and Holm 1.0.
- **Power:** 6–0 → 0.031; 7–0 → 0.016; 5–0 → 0.0625.
- **Difficulty table:** 4/4, 3/3, 2/7; 4/4, 3/3, 1/7; 4/4, 2/3, 2/7.
- **Endings and per-trial means:** endings 9/4/1, 8/6, 8/6; 9/10, 8/8, 8/8; tool calls 18.6/20.8/23.2;
  terminal commands 16.6/18.4/20.6; cut-off steps 16/21/27; elision 2/4/5.
- **Mechanism:** decode 36.7/36.7/36.0; medians 11.4/13.9/11.3; 83/82/83%; 66/78/84; 20/25/28;
  37/35/29%; 33.6k–42.7k; about 43k.
- **Concurrency and context:** get_it 983 s; unlimited_subway 729 s; 12–19%; context 32,726/31,461/30,218.
- **Gates and prompts:** 51/51 gates; 9 development trials; 17/17 first-prompt counts; 296 `pip freeze`
  lines and the openai version.
- **Hashes:** `c3cf9e34`/`af16f654`.
- **Stage C:** Table 6; 8 of 14; 7 of 22; the five within budget (63/45/64/148/226 s; bigboy 245;
  slithery 649).
- **Timeline and cost:** 23:24–07:15 UTC; 33 min; $2.63/$4.29/$2.95 = $9.87 of $20.28; $6.76 per pod and
  180 min.
- **Word count:** see above.

No number errors were found.

### Flags and exploit content (item 9)

- A grep of `paper/` (md, svg, json, py) for flag formats, `{…}` contents, hex constants and exploit
  vocabulary found only CSAW event names, the tool list in the verbatim system prompt and JSON schema
  braces.
- There are no flags, commands or step-by-step exploit content.

## Must fix

1. **R4-01 residual (§2 l.132–134):** remove the causal claim "an omitted target address and unreadable
   binary output were enough to depress measured capability to near zero". Use descriptive, non-causal
   wording.
2. **R4-01 residual (§7.3 l.625–626, §12 l.763–765):** the "far larger / far more … than between
   checkpoints" comparison brings back the harness-vs-refusal-removal contrast that REVIEW-004 asked to
   drop. The two were measured in different designs, and one side is a non-detection. Either remove it or
   state that design caveat in the same sentence. In §12, say "between two runs that differed in harness
   and budget", not "between two harnesses".
3. **R4-08 residual (§2 l.128):** "the agent harness matters as much as the model" is not supported by
   the cited works. Soften it.
4. **R4-27 residual (Appendix D row 4):** replace "verification pending" with the final cycle-4 status.

## OK

- 26 of 29 findings are VERIFIED. R4-01, R4-08 and R4-27 are PARTIAL, as above. None is NOT FIXED or
  REGRESSED.
- **Recommended, not blocking:**
  - §7.1 l.604 "nothing to unlock" → "no refusal was observed to unlock".
  - §7.3 l.639 "can improve" → "may be able to improve".
  - Cite D-23 for the 79% figure.
  - Fix the `make_figures.py` "figure 5" message.
  - Optionally web-confirm the Newcombe page range.
- **Author placeholders to fill before submission:** name, programme, supervisor, AI-policy citation,
  IRB confirmation, and the public-release decision.
- The scripts are reproducible and deterministic: outputs are byte-identical on re-run. The verbatim
  appendix is exact. The manipulation-check statement is accurate and prominent. No fabricated
  references were found, and there is no flag or exploit content in `paper/`.
