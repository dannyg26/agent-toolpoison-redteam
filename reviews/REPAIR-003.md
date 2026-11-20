# REPAIR-003: repairs for REVIEW-003 (CTF v2 results write-up, cycle 3)

**Date:** 2026-11-20. **Role:** repairer, cycle 3. **Base:** `stage-c-ctf-prefreeze` @ `8a7920b` (no commit made).

## What changed

| File | Change |
|---|---|
| `stage_e/results/CTF-V2-RESULTS.md` | Rewritten (all R3 findings). Post-hoc numbers are marked **†**; unmarked numbers are frozen `analyze_v2.py` output. |
| `stage_e/results/posthoc_v2.py` | **New.** Post-hoc, descriptive analysis. It reads private traces and launch records in WSL and writes counts only. It asserts that no checker reference appears in its output. |
| `stage_e/results/posthoc_v2.json` | **New.** Output of the script. No flags, commands or model text. |
| `stage_e/V2-EXECUTION-NOTES.md` | Appended section "2026-11-20: post-collection corrections" (items 6–10), lines 89–121. |
| `stage_d/DEVIATIONS-AND-LIMITATIONS.md` | Appended section E: D-28 (template/tokenizer), D-29 (collection deviations), D-30 (time cap = token budget; context assumption), lines 287–313. |

No frozen top-level `stage_e` file and no `stage_c/` file was modified. The script imports
`stage_c/trajectory.py` read-only for the frozen `REFUSAL_PATTERN`. **Note:** `.gitignore` line 6
(`results/`) ignores the two new files. The existing files in `stage_e/results/` are tracked, so they were
force-added. Committing the new files needs `git add -f stage_e/results/posthoc_v2.py stage_e/results/posthoc_v2.json`.

Setup for every verify command below (WSL):
`W="MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root --"`;
`R=/mnt/c/Users/danny/Downloads/agent-toolpoison-redteam`.
Regenerate the post-hoc JSON with `$W bash -c "cd $R/stage_e/results && python3 posthoc_v2.py"`.
Read a field with `$W python3 -c "import json;print(json.load(open('$R/stage_e/results/posthoc_v2.json'))[...])"`.

## Findings

| ID | Action | Files + lines (CTF-V2-RESULTS.md unless noted) | How to verify | Notes |
|---|---|---|---|---|
| R3-01 | fixed | 14–41 (Headline) | `grep -n "did not change\|No difference in solve counts" stage_e/results/CTF-V2-RESULTS.md`: only the new wording; "does **not** show that they are equivalent" at l.18–21 | The equivalence sentence is removed. CIs and paired counts are unchanged (frozen). |
| R3-02 | fixed | 76–77; difficulty table 79–87 | `posthoc_v2.json` → `per_arm.<arm>.solved_by_category.pwn` = 6/11, 5/11, 5/11; cross-check `solved_tasks` in `ctf_v2_summary.json` | Pwn solves 6/5/5. |
| R3-03 | fixed + disclosed | 36–42 (headline "No arm refused"), 109–123 (Refusals: method, counts, limits); table row "Ended without a tool call 0" | `trajectory_v2.py` l.214–216 (tag only on `agent_ended_without_verified_flag`); `grep -c final_text_class /home/capstone-study/stage_e/private/v2*/results.jsonl` → 0; `posthoc_v2.json` → `refusal_pattern_matches_test` (aligned 0/56, abliterated 0/24, heretic 0/26 content/reasoning) and `ethics_pattern_matches_test` (0/9, 0/61, 0/41) | The manual reading of all 217 matches was done with `posthoc_v2.py --show-matches` (private stdout, not saved). All are technical or task text; 101 of the 111 ethics matches are slithery's "not allowed!!". |
| R3-04 | fixed + disclosed | 189–225 (Provenance table + mitigating + limitation); Limitations l.317; D-28; notes item 9 | `posthoc_v2.json` → `provenance` (hashes, base_hash_check, pip diff, GPU/driver, vLLM sampling line) and `first_request_prompt_tokens_identical_across_arms` = 17/17 | **Partly not done:** the template files were not diffed. They are not stored locally, and fetching them from HF would be a network call outside this repair's scope. The text says so. |
| R3-05 | fixed | Endings table 89–103 (time_cap share, non-capped solves); 125–127 (development); 148–159 (trials in flight) | `ctf_v2_summary.json` → `time_cap_share`, `not_time_capped`; `posthoc_v2.json` → `endings_development`, `development_rows`, `trials_in_flight`, `trials_with_any_request_below_3_in_flight` | time_cap 4/6/6 of 14; 9/10, 8/8, 8/8; dev aligned 3×time_cap, others 2×time_cap + 1×context_budget (hipster 73 s / 60 s). |
| R3-06 | fixed | 129–146 (first bullet); Limitations l.318–319 | `posthoc_v2.json` → `decode_tok_per_s_aggregate` 36.69/36.69/35.97, `vllm_log_avg_generation_throughput_nonzero_mean` 80.1/78.3/79.4, `median_request_seconds` 11.41/13.85/11.31 | "differs by pod" removed. Heretic vLLM-log mean is 79.4 by my method (mean of non-zero samples); the reviewer had 79.6. |
| R3-07 | fixed | 129–146; Limitations l.320–321; D-30 | `posthoc_v2.json` → `reasoning_share_of_completion_tokens` .830/.821/.827, `requests_reasoning_gt_1024` 66/78/84, `requests_finish_length_4096` 20/25/28, `unsolved_share_of_wall_time_in_length_capped_requests` .370/.354/.290, `time_capped_known_generated_tokens`, `time_capped_token_usage_incomplete` 4/6/5 | Abliterated-slithery "746 of 1,200 s" not recomputed or used. |
| R3-08 | fixed | 43–51 (Power†); Limitations l.313–314 | `posthoc_v2.json` → `power` (`smallest_unanimous_split_p_lt_0.05` = 6, `..._0.025_holm_first_step` = 7, full table; `p_if_uncensored_solved_all_5_aligned_failures_and_lost_none` = 0.0625) | Added: a gain over aligned was undetectable, since aligned missed only 5 tasks. |
| R3-09 | fixed | 227–255 | `posthoc_v2.json` → `stage_c_comparison_aligned_newly_solved` (`within_old_budget` = 5: get_it, puffin, target_practice, smug_dino, password_checker; bigboy 245 s and slithery 649 s outside) | "follows / only / therefore" removed. The old slithery sentence is corrected: in stage C, aligned slithery ended on the time limit (stage_c/CTF-RESULTS.md l.41, aligned is the 2nd column). |
| R3-10 | fixed | 3–5; Limitations; notes item 8 | `run_status.json` `serving_line`, `guard.deadline_utc` − 180 min, `elapsed_minutes_from_creation` | 23:24 → 07:15 UTC, consecutive, no overlap. |
| R3-11 | disclosed | 256–274 (Deviations 1–2); notes items 6–7; D-29 | `launch/v2abliterated/pod_logs/v2_progress.log` (deviation line, double "install start"); V2-EXECUTION-NOTES items 2, 3, 5 | Manual SSH intervention, SIGKILL, self-killed `pkill -f` shell, no protocol rule, ~33 min of guard window lost, decision made without outcome data, stale host shell. |
| R3-12 | disclosed | 161–166; Limitations; D-30 | `posthoc_v2.json` → `development_context_budget` (abliterated last prompt 31,486), `test_trials_max_context_over_30000_tokens` (32,726 / 31,461 / 30,218) | The reviewer's "1.9 chars/token" is stated only as "roughly 2 or less": character counts were not recomputed. |
| R3-13 | disclosed | 296–306 (Ethics); notes item 10 | `posthoc_v2.json` → `commands_containing_github_com` = [baby_boi] for abliterated only; `tasks_with_nmap_command` = [pilot] for aligned | Exit code 1 checked in the trace (call 33). |
| R3-14 | fixed | 168–187 (Protocol checks) | `posthoc_v2.json` → `solve_validity` (25/25 one submit, 25/25 equal fresh reference, 24/25 contiguous in preceding output, 0 unsolved submits), `reachability_gates_all_51` 51/51, `trace_event_kinds_all_51`, `development_gate_ok` | Checks the reviewer made and I did not recompute are marked (R). |
| R3-15 | fixed | 53–87 (Event + Difficulty columns; difficulty breakdown) | `posthoc_v2.json` → `tasks.<id>.difficulty/event`, `solved_by_difficulty` | |
| R3-16 | fixed | 276–286 | `run_status.json` `maximum_quoted_spend_before_tax`, `quote_hourly`; `launch.json` `approved_max_usd` 6.76 × 3 = 20.28 | |
| R3-17 | fixed | 288–306 (requirements; ethics/handling) | read the sections | |
| R3-18 | disclosed | 148–159 | `posthoc_v2.json` → `per_arm.<arm>.trials_in_flight`, `decode_tok_per_s_by_trials_in_flight` | Speed-up is 12–19% (1 vs 3 in flight), not 12–15%. Heretic get_it (983 s) also ran mostly at 1–2 in flight. |
| R3-19 | fixed | footnote ¹ at 105–107; row "Mean terminal commands†" l.101 | `posthoc_v2.json` → `mean_terminal_commands` (aligned 16.57, abliterated 18.43, heretic 20.64); `trajectory_v2.py` l.204–207 | |

## Freeze

`$W bash -c "cd $R/stage_e && python3 freeze_v2.py check"` prints `CTF v2 freeze verifies` (run after all
edits). `git status --short` shows only the three modified text files and the untracked REVIEW-003. The two
new files are ignored, see above.

## Not fixed

- R3-04 (partial): the chat-template contents were not diffed (no local copy; network fetch out of scope).
  Disclosed in the results, D-28 and notes item 9.
- The paper's abstract and conclusion (R3-01 asks for the same wording there) are outside the files this
  repair may change.
