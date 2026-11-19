# REPAIR-002: repairs and disclosures for REVIEW-002 (CTF v2, stage E, pre-freeze)

**Date:** 2026-11-19. **Role:** repairer, cycle 2. **Branch / base:** `stage-c-ctf-prefreeze` @ `418edc1`
(plus the builder's uncommitted `check_v2_environment.py` change and untracked `diagnose_reachability.py`,
both now rewritten). Nothing was committed, pushed, reset or checked out.

**Limits kept.** No RunPod/cloud call, no ssh, no key file read, no `launch_*.py --launch/--check-access`,
no model call. `v2_freeze.json` was **not** written; `allow_live_model_calls` stays `false`. No change to
`stage_c/` or `stage_d/` code. One note was added to `stage_d/DEVIATIONS-AND-LIMITATIONS.md` (D-27, a stage C
disclosure). Local Docker only: sandbox runs and one cached rebuild of the v2 agent image (all layers from
cache; only the new label changed). All changed files have LF line endings (checked: no `\r`).

**Side effect to note.** The repaired `check_v2_environment.py` overwrote
`/home/capstone-study/stage_e/v2_environment_check.{json,log}`, which REVIEW-002 cited as evidence for
R2-01 (builder runs 1 and 2). Those two earlier results survive only as quoted in REVIEW-002. Rebuilding
the image with the label changed the v2 image ID from `sha256:bf3e39a2…` to `sha256:c8e12084…`.

## Headline results

| Check | Result |
|---|---|
| Offline suite `python3 -m unittest test_v2` (WSL) | **44 tests, OK** (was 19) |
| `check_v2_environment.py` (now 14 test + 3 development tasks) | **ALL OK**, `complete: true`, every reachability gate passed on attempt 1 |
| `concurrency_smoke.py 3` (3 sandboxes at once, no model) | all 3 gates pass, all commands exit 0; min available memory **6,957 MB** of 7,739, swap 0 |
| `concurrency_smoke.py 14` (full soak, 3 at a time) | all 14 gates pass, no errors; min available **6,760 MB**, max used 979 MB, swap 0, 48 s |
| `freeze_v2.py dry-run` (new; writes nothing) | all freeze inputs verify: 16 sources, 11 reused, 6 private files (+ vendor re-hash), image label = Dockerfile hash, environment-check hash |
| `launch_v2.py` (dry run, no API call) | cap **$6.76** per arm, order aligned → abliterated → heretic |
| R2-01 root cause | **not reproduced** (0 failures in 72 targeted probes + 17-task check + 17 sandboxes under concurrency); "one connection at a time" refuted (targets use `socat … fork` / xinetd); unconfirmed, mitigated by the gate |

## Verification commands

All commands run from Git Bash. `W` stands for this prefix:

```
W="MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash -c"
E=/mnt/c/Users/danny/Downloads/agent-toolpoison-redteam/stage_e
# V1 unit tests (44, all OK)
$W "cd $E && python3 -m unittest -v test_v2"
# V2 single test class or test, e.g.
$W "cd $E && python3 -m unittest -v test_v2.Reachability test_v2.Launcher.test_log_fetch_cannot_block_termination"
# V3 environment check (about 15 min; rewrites /home/capstone-study/stage_e/v2_environment_check.json)
$W "cd $E && python3 check_v2_environment.py"
# V4 concurrency smoke (3 sandboxes at once; rewrites concurrency_smoke.json)
$W "cd $E && python3 concurrency_smoke.py 3"
# V5 freeze inputs without writing a freeze
$W "cd $E && python3 freeze_v2.py dry-run && test ! -e v2_freeze.json && grep allow_live v2_config.json"
# V6 launcher dry run (no API call)
$W "cd $E && python3 launch_v2.py"
# V7 no CR in changed files; pod script parses
$W "cd $E && ! grep -l \$'\\r' *.py *.md *.json *.sh ../stage_d/DEVIATIONS-AND-LIMITATIONS.md ../reviews/REPAIR-002.md && bash -n v2_pod.sh"
```

Below, `T.<Class>.<test>` means `test_v2.<Class>.<test>` run with V2. Line numbers refer to the files as
left by this repair.

## Findings

| ID | Action | Files and lines | How to verify | Notes |
|---|---|---|---|---|
| R2-01 | **fixed** (gate) + root cause investigated, **unconfirmed** | `environment_v2.py` 32-40 (`TargetUnreachable`, constants), 94-107 (`wait_reachable`); `run_arm_v2.py` 99-105 (gate before `run_trajectory`, i.e. before the trial clock), 110-114 (reason `target_unreachable`); `check_v2_environment.py` 31-53 (same gate); `diagnose_reachability.py` (rewritten); `V2-EXECUTION-NOTES.md` (findings); `V2-PROTOCOL.md` item 9 | `T.Reachability.test_gate_retries_then_passes`, `test_gate_gives_up_after_ten`; `T.Runner.test_unreachable_target_is_infrastructure_failure` (no model call before the gate; trace event `reachability_gate`, attempts 10); `T.Runner.test_concurrent_phase_records_every_task_once` (14 gate events with attempts); V3 (`reachability_attempts` per task); `cat /home/capstone-study/stage_e/reachability_diagnosis.log` | Gate: after `wait_healthy`, fresh `nc -z -w 3 box port` from the agent container, up to 10 tries 3 s apart. Diagnosis: 12 sandboxes × 6 probes on pilot/get_it/bigboy/unlimited_subway, 72/72 nc and 72/72 python OK; DNS fine (`127.0.0.11`); `docker exec` costs about 1 s on this host. Pilot/get_it/bigboy use `socat … fork`, unlimited_subway xinetd, so the builder's "one connection at a time" comment is wrong. Stage C lacked the gate: disclosed as `stage_d/DEVIATIONS-AND-LIMITATIONS.md` D-27. |
| R2-02 | **fixed** | `launch_v2.py` 31-60 (`POD_LOG_FILES`, `fetch_logs`: 30 s per fetch, 180 s total, catches every exception), 205-216 (`finally`: fetch inside `try/except`, `C.terminate` in an inner `finally`) | `T.Launcher.test_log_fetch_cannot_block_termination` (a pod whose `run` always raises `TimeoutExpired`: `fetch_logs` returns errors; full `launch()` still calls `terminate` and writes `run_status.json` with `terminated: true`) | Mirrors `stage_c/launch_ctf.fetch_logs`. |
| R2-03 | **fixed** (builder decision) | `v2_config.json` (`wall_cap_seconds` 1200, `hard_session_minutes` 180; dev cap stays 600); `V2-PROTOCOL.md` item 6, "Execution", "Limitations", "Cost"; `trajectory_v2.py` docstring item 3; `analyze_v2.py` 98-102 (`time_cap_share`, `not_time_capped`) | `T.Launcher.test_budget_package_and_shell` (budget (2.22, 6.76), 180 min); V6; `T.Analysis.test_three_arm_summary` (time_cap share, solves among non-capped) | Count limits unchanged (50 / 65,536 / 4,096 / 3). "Counts are primary" wording removed; protocol now says all limits apply, the ending reason is reported, and time is concurrency-dependent (limitation). |
| R2-04 | **fixed** | `trajectory_v2.py` 108-118 (`command_is_encodable`), 236-240 (NUL/unencodable command → `{'error': 'invalid command bytes'}`, counts one tool call, `invalid_command_calls`) | `T.Robustness.test_nul_and_surrogate_commands_are_tool_errors` (NUL and `\ud800`: trial continues and solves; also asserts the stage C runner itself still raises `ValueError` on NUL) | Not an infrastructure failure. |
| R2-05 | **fixed** | `trajectory_v2.py` 1-31 (documented rule and 2.2 chars/token assumption), 63-64 (`MESSAGE_CHAR_BUDGET` 60,000, `ASSUMED_CHARS_PER_TOKEN`), 88-105 (`serialized_chars`: whole message incl. assistant text and tool-call arguments, `json.dumps` with ASCII escaping; `elide_history` against it), 263 (tool content `ensure_ascii=False`); `V2-PROTOCOL.md` item 5 | `T.Elision.test_assistant_text_and_escaping_are_counted`, `T.Elision.test_budget_constants_fit_context` (60,000/2.2 + 1,000 + 4,096 < 32,768), `T.Robustness.test_fifty_near_limit_non_ascii_steps_stay_in_budget` (50 steps of ~15 K CJK/Latin-1 output: every request within budget or only the newest output live; content has real characters, no `\u` escapes) | `context_budget` from the server is kept as the fallback ending. Text that tokenises below 2.2 chars/token can still overflow; stated in the protocol. |
| R2-06 | **fixed** | `freeze_v2.py` 23-25 (`PRIVATE` adds `asset_hashes.json`, `development_asset_hashes.json`; all mandatory), 39-60 (`private_hashes`: missing file is an error; re-hashes every vendor file and checker template as stage C did), 68-79 (`environment_check`: all_ok, same image, exactly the 17 tasks; hashed), 82-89 (image label must equal Dockerfile hash), 102-115 (`KEYS`, verify rejects freezes lacking a key), 130-135 (`dry-run`); new `build_agent_v2.py` (builds with label `org.capstone.v2.dockerfile_sha256`, writes `agent_v2_build.json`); `environment_v2.py` 47-52 | `T.Freeze.*` (4 tests); V5 | Image rebuilt from cache with the label: `sha256:c8e12084…`, label `29686e19…`. |
| R2-07 | **fixed** (builder decision) | `v2_config.json` `arm_order` = aligned, abliterated, heretic; `V2-PROTOCOL.md` "Execution" | V6 prints the order | Control first. |
| R2-08 | **fixed** (builder decision) | `run_arm_v2.py` 40-47 (`development_gate`), 178-184 (gate used in `main`, result written to `development_gate.json`); `trajectory_v2.py` 237, 253 (`parsed_tool_calls`); `V2-PROTOCOL.md` "Development gate" | `T.Runner.test_development_gate_checks_infrastructure_only` (refusals on 2 of 3 dev tasks pass; zero parsed calls everywhere fails; any infra failure fails) | Model behaviour never blocks the test phase. |
| R2-09 | **fixed** | `v2_pod.sh` 1-9 (header), 27-31 (`alive` via `ps -o stat=`, zombie = dead), 32-42 (`wait_up` returns 0/1/2), 43-49 (`stop_server` kills the setsid process group), 54-69 (`start_server`: timeout → kill + `serve FAILED (timeout)`, no fallback; fallback only after process death), 118-120 (main only when executed) | `bash -n` (V7); `T.Launcher.test_pod_driver_timeout_kills_server_and_never_falls_back` (fake hung server: one serve, no fallback, process killed), `test_pod_driver_falls_back_only_after_process_death`, `test_pod_driver_serving`, `test_pod_driver_keeps_fallback_for_load_failure_only` | Tests source the real script with fake `serve`/`healthy`. |
| R2-10 | **disclosed**; partly fixed | `V2-PROTOCOL.md` "Limitations" (cross-run drift); `v2_pod.sh` 70-96 (`nvidia-smi` and tokenizer hashes recorded); `launch_v2.py` 31-33 (pip-freeze, nvidia-smi fetched) | `grep -n "Cross-run drift" stage_e/V2-PROTOCOL.md` | **Deferred:** installing arms 2-3 with arm 1's `pip-freeze.txt` as a constraints file (needs a cross-session package-transfer path and risks resolver conflicts on a different pod image; not done pre-freeze). |
| R2-11 | **done** (smoke + soak) | new `concurrency_smoke.py`; results in `V2-EXECUTION-NOTES.md` | V4; `/home/capstone-study/stage_e/concurrency_smoke.json`, `concurrency_soak_14.json` | Idle sandboxes only: worst case 3 × (1 GB + 1 GB) ≈ 6 GB vs ≈ 6.8–7.0 GB available, so about 0.8 GB headroom at the memory limits. No `.wslconfig` change made. The `docker stats` sampler returned no rows (not investigated). |
| R2-12 | **fixed** (classification); template part **deferred** | `trajectory_v2.py` 201-215 (`finish_reason == 'length'` checked first; `tool_call_text_present` logged) | `T.Robustness.test_cutoff_takes_precedence_over_unparsed_text` | How the chat template handles a `content: None` assistant message can only be seen against vLLM; check in the development phase traces. |
| R2-13 | **fixed** | `trajectory_v2.py` 187-188 | `T.Robustness.test_token_cap_violation_is_infrastructure` | Stage C rule restored. |
| R2-14 | **fixed** | `trajectory_v2.py` 176-181 (worker `TimeoutError` → `serving_latency`) | `T.Robustness.test_transport_read_timeout_is_serving_latency` | |
| R2-15 | **fixed** | `analyze_v2.py` 13-16, 118-129 (Holm only when both primary contrasts exist; otherwise `p_holm_primary: null`, `holm_status`, `p_primary_bound_m2 = min(1, 2p)`, stage D D-01 rule); `V2-PROTOCOL.md` "Outcomes" | `T.Analysis.test_three_arm_summary` (bound 0.5 for p 0.25), `T.Analysis.test_holm_when_both_primary_contrasts_exist` | |
| R2-16 | **fixed** | `analyze_v2.py` 1-10, 41-64 (`load_rows`, `merge`; duplicates across files rejected; model/revision checked against config), 87-96 (`unobserved_reasons` block); `run_arm_v2.py` 158 (not_started rows now carry `revision`) | `T.Analysis.test_merge_rejects_duplicates_and_wrong_model` | CLI: `python3 analyze_v2.py merge OUT IN…` and `python3 analyze_v2.py IN…`. |
| R2-17 | **disclosed** | `V2-PROTOCOL.md` "Execution" (seeds), "Limitations"; `run_arm_v2.py` docstring | `grep -n "bit-reproducible" stage_e/V2-PROTOCOL.md` | |
| R2-18 | **fixed** | `run_arm_v2.py` 35 (`START_RESERVE_SECONDS = 300`), 82 | `T.Runner.test_soft_stop_reserve_covers_setup_and_teardown` | 300 s ≥ create 90 + start 90 + health 20 + gate ≤ 60 + teardown 30. Measured setup/teardown in the smoke test: about 4 s + 3 s. |
| R2-19 | **fixed** | `check_v2_environment.py` (whole file: dev tasks in discovery mode, `elf_starters_executable` in `ok`, `complete` flag, writes JSON only for a full run); `environment_v2.py` 84-92 (failed chmod raises) | V3 → `ALL OK`, 17 tasks | |
| R2-20 | **fixed** | `CTF-V2-DESIGN.md` 1-9 (SUPERSEDED banner); `V2-PROTOCOL.md` 3-5; `v2_config.json` `status` | `head -9 stage_e/CTF-V2-DESIGN.md` | Config `status` stays "draft; not frozen" with a note that the freeze commit sets it; `freeze_v2.py write` already requires `allow_live_model_calls`. |
| R2-21 | **fixed** | `trajectory_v2.py` 66-68 (C1, bidi, zero-width, BOM added); label reworded to "non-printable characters" | `T.DisplaySafe.test_c1_bidi_and_zero_width_are_replaced` | |
| R2-22 | **fixed** (recording); comparison at report time | `v2_pod.sh` 70-96 (`record_provenance`: sha256 of tokenizer_config/chat_template/tokenizer/generation_config for served and base revisions; nvidia-smi); `launch_v2.py` 63-80, 212 (SERVING line and hashes copied into `run_status.json`) | read the code; no offline test of the pod side beyond `bash -n` | |
| R2-23 | **fixed** | `launch_v2.py` 31-33 (fetch list adds guard.log, v2_pod.log, v2_guard/*, heartbeat, nvidia-smi.txt, tokenizer_hashes.json) | `T.Launcher.test_log_fetch_cannot_block_termination` (counts `POD_LOG_FILES`) | Heartbeat is fetched at the end, not read live. |
| R2-24 | **fixed** (recording) + text | `run_arm_v2.py` 36-37, 88, 95-96, 117-119 (`trials_in_flight` on every trace event); `V2-PROTOCOL.md` "Outcomes", "Limitations" | `T.Runner.test_concurrent_phase_records_every_task_once` | |
| R2-25 | **fixed** | `environment_v2.py` 109-117 (exit ≥ 125 → check container running; if not, `infrastructure_error`); `trajectory_v2.py` 123-124, 245, 270-271 (`terminal_infrastructure` reason) | `T.Reachability.test_terminal_flags_dead_agent_container`, `T.Robustness.test_dead_container_after_command_is_infrastructure` | Exit 126/127/137 from a live container still reach the model. |
| R2-26 | **disclosed** | `V2-PROTOCOL.md` end of "Why v2 differs" | `grep -n "discovery mode" stage_e/V2-PROTOCOL.md` | |
| R2-27 | **no defect**; text added | `V2-PROTOCOL.md` "Limitations" (steering text listed by source location) | — | The verbatim texts go into the final report. |
| R2-28 | **fixed** (recomputed) | `V2-PROTOCOL.md` "Cost" | read section | Worst case ≈ 155–165 min < 175-min soft stop; cap $6.76/arm, $20.28 for three. |

## Not done / for the verifier's attention

- **Deferred:** R2-10 pip constraints file across arms; R2-12 template behaviour for a `content: None`
  assistant message (development phase only); a loaded (non-idle) memory test.
- **R2-01 root cause** stays unconfirmed; the gate mitigates and records attempts.
- `freeze_v2.py write` was not run (by rule). The freeze will now fail unless the image carries the label,
  the 17-task environment check passes on that image, and all 6 private files exist.
- Re-running V3 or V4 rewrites their JSON files; re-running V3 after a freeze changes
  `environment_check_sha256` and requires a new freeze.
