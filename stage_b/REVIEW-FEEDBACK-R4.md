# Revision 4 prelaunch review, 2026-11-17

Decision: ACCEPT the proposed study for prelaunch readiness, subject to the
existing freeze/publication, live preflight, funding and user-authorization
conditions. This review does not authorize or perform a paid launch.

## R3 finding

FIXED. heldout_runtime.supervise now enforces an elapsed-time bound outside the
synchronous SDK call. The harness runs in a child process; the supervisor sends
SIGTERM at the configured cutoff and escalates after five seconds. The parent
runner remains available to report and archive. The protocol correctly describes
SDK network timeouts as best effort rather than a total elapsed-time guarantee.
Completed records are retained, missing outcomes remain unknown, and supervisor
events are included in the report.

The runner invokes supervise for harness phases and GNU timeout for its tool
checks. The configured work cutoff remains 184 minutes after pod creation, with
30 seconds of supervisor grace and five seconds for escalation, before the
189-minute hard pod deadline.

## Verification

Ran all 14 test groups with the existing local AgentDojo environment; all passed
without skips. In the real-SDK localhost regressions:

- the in-process characterization returned at 1.83 seconds after a 1.2-second
  soft stop, correctly demonstrating the limitation;
- the supervised slow-response child was stopped after 3.01 seconds for a
  3.0-second cutoff;
- the supervised harness stopped about 1.1 seconds after its soft stop with
  one-second test grace, retained ten completed records, reported 22 unknown
  outcomes, and generated the planned-inventory report and supervisor event;
- a normally finishing child retained its exit code.

Both the held-out and original-pilot freeze checks passed. The no-API launcher
dry run and cost worksheet reproduced. Tests ran locally on Windows; the
production POSIX process-group branch was inspected in source, not executed
on a rented Linux pod. No additional paid validation is requested by this review.

## Professor requirements and budget

The proposed recent uncensored Qwen3.8 main attacker, matched aligned control
and benign tool-use assessment address the three stated requirements. The
planned capability results remain evidence to collect, not an already-passed
gate or comprehensive validation. No change to models, cases or analysis is
requested.

The worksheet remains $3.14 normal and $6.52 conservative. At the ceiling rate,
189 minutes costs $6.993; including the stated allowance is approximately $7.09,
inside $10 assuming successful termination. The disclosed extreme scenario may
not finish. The budget is a configured spending target, not an unconditional
guarantee against provider/termination failure. No live price or balance was
re-queried in this review.

## Remaining issues and next steps

No remaining blocking or non-blocking issue identified within this R3-focused
re-review. No further design revision or enlarged experiment is requested.

Before collection, freeze and externally timestamp the exact final procedure
by committing and pushing it. Refresh the existing read-only checks for price,
balance, existing pods and current spend. The configured launch minimum remains
$7.50, and the user's approval of the concrete paid launch is still required.
Do not change the protocol in response to newly observed held-out outcomes.

Nothing was committed, rented or collected during this review. Only this review
note was added; implementation and frozen files were left unchanged.
