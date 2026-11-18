# Revision 2 prelaunch review, 2026-11-17

Reviewed REVIEW-BRIEF.md revision 2, HELDOUT-PROTOCOL.md, the new source files and
the unchanged harness/guard helpers. No models or provider APIs were called;
no files in either frozen procedure were changed, and nothing was committed.

Decision: the proposed model choices address the professor's three stated
requirements, and the configured spending target fits $10. Do not launch yet:
the missing-data reporting and deadline/recovery defects below need local fixes.
No expansion of the study or additional paid tests is requested.

## Six previous revisions

1. FIXED for the primary analysis: all 32 pairs are retained, complete-pair
   inference is conditional, and a directional verdict requires rejection under
   the completion least favourable to that direction. The supplied missing-data
   enumeration tests passed. Secondary/capability handling has a separate bug below.
2. FIXED: distinct user-task clusters, fixed/stochastic components, independence
   and exchangeability assumptions, and limited generalization are stated.
3. FIXED: all six planning-power values reproduce. CI widths are identified as
   planning approximations, not guaranteed Tango widths.
4. PARTLY FIXED: the worksheet reproduces, both actual timers use the new
   configuration, and both freeze checks pass. The bootstrap's purported exact
   deadline verification is not exact; the retry allowance is also not a bound.
5. PARTLY FIXED: request-only retries, balanced blocks and no 16-case substitution
   are specified. In-flight requests/retries can prevent graceful shutdown, and
   interrupted result-file recovery is not implemented.
6. FIXED: extractable insertions and heuristic detected exposure are described
   operationally rather than as refusal/compliance or verified exposure.

## Remaining issues

### 1. BLOCKING: unobserved outcomes become failures in secondary/capability reports

`analyze_heldout.py:207` always outputs
`successes_wilson_95ci_over_planned = [succ, len(per_case), wilson(...)]`.
Unknown attack outcomes therefore enter an ordinary success-rate interval as
failures. With no campaign records at all, the primary correctly reports 32
incomplete pairs and WITHHELD, but the secondary arm result is 0/32 with a Wilson
95% CI [0, 0.107179]. That is not an interval for the unknown attack success rate.
Observed successes out of planned cases can be a labelled observed-success count
or lower bound, but an ordinary Wilson interval cannot represent all unknown
outcomes as observed negatives.

Capability reporting (`analyze_heldout.py:229` onward) uses the union of observed
keys, and `ok(None)` is false. Synthetic example: supply twelve successful
uncensored capability records and no aligned records. The report claims:

- uncensored 12/12, CI [0.757506, 1];
- aligned 0/12, CI [0, 0.242494], with zero limits/errors;
- paired difference +1, Tango CI [0.515012, 1], McNemar p=0.00048828125.

The aligned assessment never ran. Its rate and comparison are unknown, not zero.
This is a plausible partial-run state because the aligned capability phase occurs
after the first uncensored attack block.

Fix: use the frozen planned capability task inventory; retain missing/error/limit
states separately from observed benchmark success and failure. Do not turn absent
records into negative outcomes. Supply identification bounds or clearly conditional
intervals as appropriate, and do not manufacture paired capability results for
unobserved tasks. Apply the same missing/limited-outcome discipline to baseline
rates. Add regression tests for absent arms, absent tasks, and limited episodes.

### 2. BLOCKING: the deadline sequence and partial-file recovery are not supported

The protocol says the guard requests a stop 60 seconds before termination, then
interrupted units are recorded, the runner archives and the laptop downloads.
However, `harness.py` only checks the stop file before units/candidates; an
in-flight request can run for 300 seconds and `_with_retries` has no stop/deadline
check. `ThreadPoolExecutor` waits for running futures. The runner cannot archive
until that command returns; hard pod deletion can arrive first. The local
controller itself begins termination 15 seconds before the guard's hard deadline.

A virtual-clock test of the actual retry helper produced request starts at
0, 305, 615 and 935 seconds, finishing in error at 1,235 seconds. After the first
timeout sets the synthetic stop flag, all three retries still start. The extra
retry time is 935 seconds (15m35s), exceeding the six-minute reserve. A single
four-timeout sequence takes 20m35s. The protocol's claim that the time retries
"can take is covered by the 6-minute reserve" is therefore false as a bound.

Separately, `heldout_tools.records` unconditionally calls json.loads on every
line. Writing a trailing partial record such as `{"key":` makes the full report
raise JSONDecodeError, instead of reporting the corresponding case incomplete.
Such a tail is a possible outcome of interrupted writing or a live file download.

Fix: implement a held-out-specific deadline-aware request/drain path while
preserving frozen pilot files. Do not start retries or target requests after the
soft stop; cap remaining request time so archival/download has a real reserve.
Handle interrupted records safely: preserve valid complete records, explicitly
record a trailing partial-line diagnostic, and do not silently ignore arbitrary
interior corruption. Generate a planned-inventory report from the downloaded
partial data even if the runner never reaches its final analysis command.
Test STOP_REQUESTED during an active request, timeout/retry handling near the
deadline, and truncated final JSONL data. Describe the six-minute figure as a
scenario allowance unless it is actually enforced as a retry budget.

### 3. NON-BLOCKING validation overclaim: the bootstrap accepts a 160-minute timer

Section 0 says setup is refused unless the armed deadline is the 189-minute cap.
`bootstrap_heldout.verify_guard_deadline` instead accepts a 30-minute range
relative to now, without reading the actual pod creation time. With
`now=createdAt+10s` and `deadline_epoch=createdAt+160min`, it accepts the deadline.
The `counts_from` string is checked, not the claimed time origin.

The actual unchanged guard computes the correct deadline, and the two timer
calculations agree; this finding does not establish an actual spending overrun.
It does establish that the advertised verification is weaker than described.
Compare against the actual authenticated createdAt plus the configured duration
within a small clock tolerance, and test an incorrect 160-minute timer. Do not
substitute a self-reported string for verification of the origin.

### 4. NON-BLOCKING protocol inconsistency: additional McNemar tests are emitted

The normative protocol says secondary outcomes are descriptive "with no further
tests" and lists no capability hypothesis test. `paired_summary` automatically
adds a McNemar p-value to first-candidate results and capability results. The
brief explicitly promises a capability McNemar test, whereas the normative
protocol specifies a descriptive paired table.

Fix: omit hypothesis-test p-values from these secondary/capability summaries to
follow the protocol. Keep the primary test and missing-outcome sensitivity tests.
There is no need to add more tests or a new multiplicity procedure.

## Professor alignment and cost

The proposed main attacker is the recent publisher-described uncensored Qwen3.8
derivative, with an aligned control and real benign tool-use assessment. The
attacker's attack-time interface is text generation with feedback, as disclosed;
the professor's supplied requirements do not explicitly require it to call tools
during the attack. The capability check is evidence to be collected, not an
already-passed gate. No human validation or extra benchmark is requested.

The reproduced worksheet gives 85.0 minutes/$3.14 in its normal scenario and
176.3 minutes/$6.52 in its conservative scenario. The configured cutoff is
189 minutes at <=$2.22/hour, or $6.993, and $7.093 including the $0.10 allowance
(rounded to $7.09). This is inside $10. The extreme scenario exceeds the cutoff;
completion is not guaranteed. An actual provider/termination failure is not
bounded by a $0.10 allowance, so describe $7.09 as the configured estimate under
successful termination rather than an unconditional worst-case guarantee.

The brief's last reported balance is $3.0648, with a launch minimum of $7.50;
the rounded top-up shortfall is $4.44 if a paid launch is later approved. No
current balance or price was re-queried in this review.

## Verification performed

- Ran test_heldout.py in the existing AgentDojo environment: all eight supplied
  test groups passed, including the scripted 32-pair end-to-end test.
- Reproduced the cost worksheet, six-row exact-power table and no-API launcher
  dry run.
- Both held-out and original-pilot freeze checks passed.
- Ran additional synthetic tests for completely absent campaign data, an absent
  capability arm, a partial last JSONL line, the 160-minute guard check and four
  virtual 300-second timeouts. These produced the counterexamples above.

Please fix these narrowly scoped local issues, update the protocol/brief where
needed, add the regression cases, and regenerate the held-out freeze. Keep the
existing models, budget and completed pilot unchanged. Before any approved new
collection, commit and push the final frozen procedure for an external timestamp.
