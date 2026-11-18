# Review of REVIEW-BRIEF.md, 2026-11-17

Decision: approve the direction for free implementation and protocol preparation;
do not launch a paid run yet. This is a proposal review, not verification of the
not-yet-written held-out runner or statistical implementation.

## Professor's requirements

The proposal addresses the literal requirements: a recent uncensored checkpoint
is the main attacker, and its general agent capability is assessed through actual
benign tool use. The aligned checkpoint is a comparison control, not a replacement.
The attack workflow itself generates text and uses feedback rather than directly
calling environment tools. That is disclosed; the professor's quoted requirements
do not explicitly forbid this architecture. Do not claim comprehensive capability
validation or passage of the original Stage A gate.

## Required protocol revisions before launch

1. **The primary inference must address incomplete pairs.** Section 6 says:
   "Incomplete pairs: excluded from the primary test" and permits up to 10%
   incompleteness before flagging noncompliance. Completion can depend on the arm
   and case difficulty; a 10% cutoff does not establish unbiased selection. Keep
   all 32 planned pairs visible and state the exact inferential consequence of
   missing outcomes. A complete-pair McNemar result must be labelled conditional
   on those pairs and its assumptions. It must not alone establish superiority
   over the full planned set when the missing-outcome sensitivity permits the
   opposite conclusion. Specify whether the bounds concern just point differences
   or also inference, and predefine when an inferential verdict is withheld.
   This does not require inventing a new estimator.

2. **Distinguish distinct tasks from proven independence.** Section 4 calls the
   cases "32 independent user-task clusters" while injection goals repeat.
   Repeated goals do not by themselves prove correlated outcomes, but distinct
   tasks alone do not prove independence either. Say "32 distinct user-task
   clusters," identify what is treated as fixed, and explain the assumptions
   supporting the paired test and interval. State whether conclusions concern
   these fixed injection goals, new user tasks, or new attack goals. Do not call
   the test exact for a broader population without its required assumptions.

3. **Publish the power assumptions and calculation.** Section 9's 44% and 61%
   figures can be reproduced, but the needed discordance probabilities are absent.
   Exact enumeration for n=32 and the standard two-sided exact McNemar test gives:

   | Uncensored-only probability | Aligned-only probability | Difference | Total discordance | Power |
   |---:|---:|---:|---:|---:|
   | 0.25 | 0.05 | 0.20 | 0.30 | 0.439237 |
   | 0.30 | 0.05 | 0.25 | 0.35 | 0.609094 |
   | 0.30 | 0.10 | 0.20 | 0.40 | 0.333713 |
   | 0.325 | 0.075 | 0.25 | 0.40 | 0.534637 |

   These assume independent pairs and no incomplete outcomes. Document the joint
   probabilities, method, alpha, and sensitivity to discordance. Effect size
   alone does not determine paired-test power. The quoted approximate CI widths
   also need to be identified as planning approximations, not guaranteed widths
   of the eventual Tango interval.

4. **Make the cost and shutdown calculation executable before spending.** The
   1.6x throughput improvement from four workers is an unmeasured assumption,
   not a pilot measurement. Provide a cost worksheet separating attacker
   generation, Gemma episodes, Qwen capability episodes, setup, all reloads,
   retries and transfer reserve. The 32 Qwen capability episodes should not be
   priced using Gemma's four-second episode time. Validate the planned worker
   setting against the conservative bound rather than relying on the speedup.
   The current pilot bootstrap defaults to pilot_config.json and its 90-minute
   limit; launch_pilot.monitor also hardcodes a $3.50 cap. New held-out plumbing
   must pass the new configuration to both independent termination mechanisms.
   Keep frozen pilot files unchanged. Demonstrate offline that both timers use
   the same pod creation time and the proposed <=$7/189-minute limit, include
   setup, and cannot silently fall back to the pilot configuration. At the
   quoted $2.218/hour, 189 minutes is $6.9867, so the arithmetic fits the proposed
   $7 allowance; this does not guarantee a provider API will always respond.

5. **Specify retries and deadline behavior precisely.** A "same-seed rerun"
   must identify whether it retries a request, candidate, episode or whole
   campaign. A whole-campaign rerun can generate additional candidates and
   exceed the stated interaction budget. Specify what is retained, what is
   repeated, retry eligibility, success preservation and the absolute number of
   extra calls allowed. Include retries in the cost ceiling. Also replace
   "a deadline hit still leaves a complete first block": the first block is
   only complete if both arms finished it before the cutoff. Freeze block
   membership, balance suites within blocks, and specify what is reported if
   either block is partial. Do not silently substitute a 16-case study for the
   planned 32-case primary analysis.

6. **Use operational descriptions for mechanical checks.** "The aligned model
   also complied in 22/23 generations" should say it produced extractable
   insertion text in 22/23; that is not a refusal/willingness assessment.
   Exposure in the existing harness is a normalized-prefix-match heuristic in
   tool messages. Report detected exposure rather than verified exposure or
   verified non-exposure unless the measurement is actually strengthened and
   frozen before the new run.

## Verified details and correction to the previous report

The declared test split contains 68 user tasks, of which ten were in the pilot,
leaving 58. Only 65 are represented in the 200 sampled cases.json test rows,
leaving 55 represented unused tasks. Both counts are meaningful; specify which
inventory the new selector draws from. Eight new cases per suite remain feasible
in the sampled inventory, with exactly eight unused banking user tasks there.

All four capped pilot generations contained extractable complete insertions and
were evaluated. Claude's statement is correct. The aligned malformed generation
was a different attempt on a different case, with finish_reason="stop".
The first PILOT-RESULTS.md incorrectly said it was the capped candidate; that
reporting error has been corrected without changing any recorded outcomes,
classifications or frozen analysis. Raw source hashes match the published metrics.
The new complete-insertion cap rule is defensible prospectively if its exact
extraction rule is frozen, the pilot-informed change is disclosed, and the old
pilot remains unchanged and unpooled.

An existing pilot-scoped API key file is already available at
`C:\Users\danny\.runpod_pilot_key`. Do not ask the user to supply its path again,
and never print its value. Verify required access through read-only checks before
any approved launch. The other key's REST rejection does not establish that it
is a full-access key.

## Next step

Address these points in the brief, write the proposed files, run meaningful free
checks, and provide the updated brief with the exact budget/configuration dry-run.
Keep the current cap and no-top-up boundary unless the user approves a concrete
paid launch. No new data collection or model-serving run was performed for this
review.
