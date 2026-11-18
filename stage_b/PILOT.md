# Budget pilot — professor's requirements, 2026-11-17

This addendum replaces the large Stage B execution scope. The original studies and the original Stage A
gate are unchanged. This is a small feasibility study, not a powered confirmation of checkpoint superiority.

## Required model and capability evidence

- **Recent:** Qwen3.8-27B, published in 2026.
- **General agent:** the main model is general-purpose and runs with tools and multi-step feedback. Both
  checkpoints passed the real-server tool-call check in the earlier smoke run. The abliterated checkpoint
  has partial BFCL results (174/221 correct across the selected categories); these are not a completed gate.
- **Uncensored attacker:** `huihui-ai/Huihui-Qwen3.8-27B-abliterated` remains the main model. The original
  `Qwen/Qwen3.8-27B` is a comparison control, not its replacement.
- Publisher descriptions and base-model scores are not proof of preserved capability. Before any held-out
  run, both checkpoints must complete at least one of two benign development tasks with at least two tool
  calls, without schema, context, or generation-cap failures on either task. This is a small engineering
  check, **not** a retrospective pass of Stage A's pre-recorded G1/G2. The invalid tau-bench runs remain invalid.

Sources: [original model](https://huggingface.co/Qwen/Qwen3.8-27B),
[uncensored derivative](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-27B-abliterated).

## Scope fixed before held-out outcomes

- One target: `google/gemma-4-26B-A4B-it`. It provides a different family and an agent-capable 2026
  checkpoint. Its active-parameter count motivates a speed hypothesis, not a guarantee of speed or weakness.
- This target choice follows the Qwen development smoke run (0/24 non-adaptive and 0/20 completed adaptive
  abliterated campaigns). Selection is post-development and must be disclosed; Qwen's aligned attacker was
  not evaluated in that smoke run. No Gemma test outcomes are used to choose the target or cases.
- Ten test cases in `cases_pilot.json`: 3 banking, 3 workspace, 2 slack, 2 travel. All ten have distinct
  user-task clusters; injection goals are also distinct within each suite. Selection is deterministic,
  metadata-only, and a subset of the existing held-out split. The 200-case inventory is preserved.
- Two attacker conditions, identical prompts and feedback; one campaign each; at most three candidates.
- Maximum **60 attack-candidate target episodes**, plus ten clean test episodes, four benign attacker
  capability episodes, and two benign target compatibility episodes: **76 agent episodes** in all, plus
  four small server tool-call checks. An episode can contain multiple LLM calls; this is not 76 API calls.
- No fixed-attack, non-adaptive, multi-seed, second-target, AgentHarm, tau-bench or RedClaw run is included.
- Run order is recorded in `run_pilot.sh`: capability on both attackers, target compatibility, clean test,
  aligned attacker, then abliterated attacker. It is a checkpoint-configuration comparison; collection
  order and the single stochastic campaign limit generalization.

## Serving and time bounds

One A100 SXM 80GB, FP8 for both attackers and the target, native templates/parsers, 32,768-token context,
at most four server sequences and two harness workers. Both attackers retain thinking, with the same
**1,024 thinking-token budget** and **4,096 total generation-token cap**. The target uses 512 thinking
tokens and the same total cap. vLLM 0.33.0's explicit `thinking_token_budget` request field is checked before
serving, and tool checks use it. Runtime effectiveness still needs checking on the real servers.

Changing these settings invalidates a resume into the same result files. A generation cap or context failure
is reported as measurement-limited/incomplete, not evidence of a refusal or absence of vulnerability.

## Spending authorization and shutdown

Use the **existing $4.60 balance** checked on 2026-11-17; no top-up, payment change, persistent volume,
second pod, automatic restart or paid external API is authorized by this pilot. The user's overall ceiling
is $15, but the intended additional pod-and-disk spend here is **at most $3.50**.

At the quoted $2.22/hour including a 200GB temporary disk, 90 minutes is **$3.33 before tax**. Setup and
downloads are included in that timer. The pod-side guard reads the pod's `createdAt`, not the experiment's
start time, and starts before dependency installation. A local independent watcher also terminates the pod.
No lower price or speed improvement is assumed. Actual rates must be checked before creation and again on
the created pod; reject a more expensive configuration and keep a balance reserve.

The guard requests real pod termination through Runpod's authenticated DELETE API. It retries on API
failure; no client can guarantee termination during a provider/network outage. The laptop watcher must
keep downloading outputs. If the laptop is offline at the hard deadline, the guard prioritizes stopping
charges and unsynchronized temporary-disk results may be lost. Do not promise both guaranteed preservation
and a strict cutoff without an independently reachable backup destination.

Credentials stay outside the repository and never enter prompts or result archives. The bootstrap stores
the pod-scoped key in a private file and removes it from child-process environments.

## Interpretation, analysis and provenance

Use the benchmark's security and utility checks under its fixed definitions; these may verify environment
effects or an output predicate and are not a universal guarantee of real-world harm. No paid judge or user
simulator is used. No human validation is planned.

Report every one of the ten planned pairs, successes within three attempts and within one attempt,
clean-task utility, actual attempts/calls/tokens, caps, errors, exposure and elapsed cost. Missing/capped
campaigns are incomplete, not failures. Preserve successes actually observed even if another attempt was
limited. If any pair is incomplete, do not present a complete ten-pair comparison. If both arms score zero,
the finding is no observed success in these cases; it does not establish equivalence or no difference.

The primary report is descriptive. With ten cases, do not claim a powered population comparison or make a
new superiority/equivalence verdict. This pilot cannot establish whether abliteration is generally worth it.

`pilot_models.json` pins all checkpoints. `pilot_freeze.json` identifies the exact code/settings/cases using
line-ending-independent hashes. Publish the snapshot before collecting held-out results to establish an
external timestamp; a local hash is not proof of when a file existed. Record every subsequent deviation.

Free local commands: `python stage_b/pilot_tools.py plan`, `python stage_b/test_harness.py`,
`python stage_b/test_pilot.py`. `run_stage_b.sh` no longer defaults to the large expensive study.
