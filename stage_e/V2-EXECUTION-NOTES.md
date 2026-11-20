# CTF v2 execution notes (pre-freeze; not part of the frozen protocol)

`freeze_v2.sources()` excludes files whose names start with `V2-EXECUTION`, so these notes can grow during
collection without breaking the freeze. Nothing here is a pre-registered rule; `V2-PROTOCOL.md` governs.

## 2026-11-19: R2-01 first-connection reachability, root-cause investigation (repair cycle 2)

**What was seen (before this repair).** The builder's environment check probed each target once with a
fresh `nc -z -w 5` from the agent container, right after the stage C `wait_healthy()` (a python
`socket.create_connection` with 1 s timeout, retried for up to 20 s) had passed. Run 1: pilot and get_it
reported CLOSED. Run 2 (3 attempts): bigboy and unlimited_subway each needed 2 attempts. So 4 different
tasks failed a first fresh connection across 2 runs.

**The "one connection at a time" explanation is refuted.** The vendored target definitions show:
pilot runs `socat -T10 TCP-LISTEN:8024,reuseaddr,fork EXEC:/home/pilot/pilot`; get_it and bigboy run
`socat -T60 TCP-LISTEN:<port>,reuseaddr,fork,su=<user> EXEC:<run.sh>,pty`; unlimited_subway runs xinetd.
All of these accept concurrent connections (`fork` / xinetd), so the health probe's connection cannot
block the next one.

**Targeted diagnosis (no model).** `diagnose_reachability.py 3 pilot get_it bigboy unlimited_subway`:
12 sandbox starts, 6 probes each, 3 s apart, starting 0.6–3.9 s after the health probe passed. Each
probe recorded `getent hosts`, `nc -vz -w 3` (text and exit code) and a python connect.
Result: **72/72 nc probes and 72/72 python probes succeeded; 0 failures**; every name resolved to the
target's address on the isolated network (embedded Docker DNS `127.0.0.11`, ExtServers `127.0.0.1`). A
second timing probe (pilot, unlimited_subway; 5 repetitions each) showed `docker exec` itself costs about
0.8–1.4 s per call on this host (even `true`), and `getent ahosts` (IPv4+IPv6), `getent ahostsv4`,
`nc -z` and python connect all completed in about 0.2–1.4 s with exit code 0. No DNS stall was seen.
Raw data: `/home/capstone-study/stage_e/reachability_diagnosis.{jsonl,log}`.

**Conclusion.** The transient did not reproduce in 72 targeted probes, in the repaired 17-task environment
check, or in the concurrency smoke test (results below). The root cause is **unconfirmed**. Candidates
consistent with the evidence: host load at the time of the builder's runs (sandbox start on this host
already takes 7–17 s and `docker exec` about 1 s), or a target that had accepted the health connection
but was momentarily slow to accept again. It is not a per-task defect and not the "single connection"
behaviour.

**Mitigation adopted (builder decision).** `EnvironmentV2.wait_reachable()`: after `wait_healthy()`,
up to 10 fresh `nc -z -w 3` attempts 3 s apart from the agent container, before the trial clock starts;
never open means infrastructure failure `target_unreachable`; the attempt count is in every trace
(`reachability_gate` event). The check and the smoke test use the same method. Stage C had no such gate;
disclosed as stage D D-27.

## 2026-11-19: repaired environment check and concurrency smoke test (repair cycle 2, no model)

- **Agent image rebuilt with its Dockerfile label** (`build_agent_v2.py`; every layer from cache): image
  `sha256:c8e12084…`, label `org.capstone.v2.dockerfile_sha256 = 29686e19…` (= LF-normalised Dockerfile
  hash). Record: `/home/capstone-study/stage_e/agent_v2_build.json`.
- **Environment check** (`check_v2_environment.py`, 14 test + 3 development tasks, same reachability gate
  as the trials): **ALL OK**, `complete: true`; every task passed the gate on attempt 1; all ELF starters
  executable; v2 image in use; target in every prompt. `/home/capstone-study/stage_e/v2_environment_check.json`.
- **Concurrency smoke** (`concurrency_smoke.py 3`; the first three tasks of the fixed order, poem_collection,
  slithery and pilot, started together on this 8-CPU / 7.7 GB WSL host): 3 in flight; all 3 reachability
  gates passed on attempt 1; all terminal commands exit 0; sandbox start 3.8–4.3 s, health 0.3–0.4 s, gate
  0.2–0.3 s, teardown 3.2–3.5 s; minimum available memory 6,957 MB (baseline 7,085 MB), maximum used
  781 MB, swap 0. `/home/capstone-study/stage_e/concurrency_smoke.json`.
- **Full soak** (`concurrency_smoke.py 14`; all 14 test tasks, 3 at a time, as `run_phase` schedules them):
  all 14 gates passed on attempt 1, all commands exit 0, no errors; minimum available memory 6,760 MB,
  maximum used 979 MB, swap 0; 48 s wall. `/home/capstone-study/stage_e/concurrency_soak_14.json`.
- **Caveat.** The sandboxes were idle apart from four short commands, so this measures the containers'
  baseline, not a trial workload. Each container is capped at 1 GB (`mem_limit`), so 3 trials can use at
  most about 6 GB in the worst case against about 6.8–7.0 GB available: about 0.8 GB headroom in that
  worst case, ample in the measured case. The `docker stats` sampler returned no rows (not investigated;
  memory figures come from `free -m`).

## Collection log (2026-11-19/20)

1. **aligned** (session `v2aligned`, pod `1dxwsrqvwd9dg9`): 3/3 development trials (all `time_cap`, gate
   passed), then 14/14 test trials observed with no infrastructure failure. Pod terminated after 71.22 min,
   quoted $2.632. Cosmetic launcher issue: after a transient log read failure the progress poller re-prints
   all earlier pod log lines (display only; serving detection unaffected).
2. **abliterated** (session `v2abliterated`, pod `td44u69jearms5`, created 03:54:23 UTC): the frozen
   driver's `pip install vllm==0.33.0` stalled with no progress for about 33 min (pip cache stuck at 678 MB
   and /tmp at 1.2 GB; network measured fast: Hugging Face at 52 MB/s, a PyTorch wheel at 380 MB/s).
   **Infrastructure retry, before any model call:** the driver was killed with SIGKILL (no FAILED or
   DRIVER_EXIT logged), then pip; the unchanged frozen `v2_pod.sh abliterated` was restarted at 04:27:29
   UTC. The deviation line is in the pod's progress.log. A first attempt's `pkill -f` pattern matched its own
   remote shell and killed it before the restart; the second attempt used an anchored pattern. The install
   then took 2.5 min; serving at 04:38. Development 3/3 (one `context_budget`, two `time_cap`; gate passed),
   test 14/14 observed with no infrastructure failure. Pod terminated after 116.08 min, quoted $4.291
   (about $1.20 of it lost to the stalled install).
3. A stale local shell from a stage C status probe (11 h old, waiting on a dead pod's SSH) was found on the
   WSL host. It is unrelated to any trial and is cleaned up after collection.
4. **heretic** (session `v2heretic`, pod `dlnu37flr69u3h`): normal install (2.5 min) and download; served with
   its own tokenizer (no fallback). Development 3/3 (one `context_budget`, two `time_cap`; gate passed), test
   14/14 observed with no infrastructure failure. Pod terminated after 79.71 min, quoted $2.946.
5. Collection complete: all 3 arms × (3 development + 14 test) trials observed, no infrastructure failure,
   no not_started trial. Total quoted v2 spend $9.869. The stale stage C probe shell (item 3) was killed.
