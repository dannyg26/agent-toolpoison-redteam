# Stage D: three-model, four-test study (design draft)

**Status: proposal only. Nothing is frozen, no dataset is downloaded, no model is called and nothing is
spent. Stage C results stand on their own and are never pooled with stage D.**

## Decisions (2026-11-19)

- **Budget:** split into two separately frozen and approved runs. Run 1 covers tests B, C and D for all
  three models (about $6–7). Run 2 covers CTF v2 for all three models (about $7). The phase ceiling must
  be raised before run 2.
- **Third model:** `jakejb53/Qwen3.8-27B-heretic`, subject to model-card verification and a pinned revision.
- **CTF:** all three arms rerun under the v2 output rule; stage C stays a separate, completed result.

## Question

Does removing refusals from Qwen3.8-27B change (a) agentic offensive capability, (b) cybersecurity
reasoning, (c) willingness to help across benign, authorised and disallowed requests, and (d) agent
reliability and resistance to injected instructions? And does the refusal-removal method matter?

## Models (one base, two removal methods)

| Arm | Checkpoint | Method |
|---|---|---|
| Aligned | `Qwen/Qwen3.8-27B` | none (control) |
| Abliterated | `huihui-ai/Huihui-Qwen3.8-27B-abliterated` | hand-tuned directional ablation |
| Heretic | one Heretic build of the same base, chosen before freeze | optimised ablation (refusals + KL) |

Heretic candidate: `jakejb53/Qwen3.8-27B-heretic`. A listing says it was built with Heretic v1.4.0 and
reports 0/100 refusals and KL divergence 0.0236. Before freezing, the model card must confirm:
(1) the base is `Qwen/Qwen3.8-27B` and not a merge or fine-tune; (2) the license; (3) a pinned
revision; and (4) that the weights serve in vLLM at FP8. Merged "Heretic/Fusion" builds are excluded
because they change more than refusals. All arms: FP8, the same vLLM, sampling and thinking settings.

## Tests

### A: agentic CTF (stage C harness)
- 14 CTFTiny web/pwn tasks, fresh secret per trial, the same isolation and grading.
- **Required fix before reuse:** tool output must not let one binary dump fill the context. Options:
  printable-only output with a hex summary of non-printable bytes, or an 8 KB per-call cap. Because this
  changes the protocol, all three arms rerun under it as **CTF v2**; stage C is not reused as an arm.
- Optional if budget allows: 2 trajectories per task, to separate task difficulty from sampling noise.
- Metric: solves out of 14 per arm, with exact intervals; descriptive paired table.

**Candidate replacement or addition for run 2: Cybench** (Zhang et al., arXiv 2408.08926;
github.com/andyzorigin/cybench; also ported to UK AISI Inspect Evals).
- 40 professional CTF tasks from 4 competitions, across crypto, web, reversing, forensics, misc and pwn.
- Difficulty is anchored to human **first-solve time**, so results read as "hardest task solved" against a
  human reference, not only a raw count.
- **Subtask-guided mode:** each task has sequential subtasks with answers, giving partial credit. That
  directly addresses stage C's floor effect, where 12 of 14 tasks were unsolved by both arms.
- Agent acts from a Kali container via bash and network calls against task servers; this matches our design.

Open issues to settle before choosing it:
1. **Static answer keys.** Unlike our fresh-secret CTFTiny setup, Cybench checks fixed flags and subtask
   answers, and the tasks have public writeups. That is a memorisation risk; we would need per-trial
   fresh flags where the task allows, or to report contamination as a limitation.
2. **Cost.** 40 tasks × 3 arms is about 3× CTFTiny's GPU time at our budget. A fixed subset chosen in
   advance (for example, stratified by category and first-solve time) may be needed.
3. **License and setup:** check the repository license, Docker requirements (some tasks run several
   services) and whether the Inspect port can drive an OpenAI-compatible vLLM endpoint.
4. **Isolation:** reapply the stage C rules (internal networks, no Docker socket, non-root agent) to every
   Cybench task, rather than running the upstream compose files as-is.

### B: technical reasoning (no tools)
- **Knowledge (answer keys):** CyberMetric-500 (multiple choice, human-validated; GitHub CyberMetric) and
  the WMDP-cyber split (multiple choice; proxy for offensive knowledge). Score = exact letter match.
- **Secure coding (executable tests):** CWEval. Each task runs functionality tests and security tests;
  report Func@1 and Func-Sec@1. BaxBench (392 backend tasks with end-to-end exploits) is stronger but
  much heavier; consider a fixed subset only if CWEval proves too easy or too hard in development.
- Why: separates reasoning quality from agent execution. If the abliterated arms keep the same B scores,
  ablation did not damage reasoning (MMLU-Pro claims for these checkpoints are third-party and unverified).

### C: refusal behaviour, scored separately from correctness
Three request strata, each from an existing public set:
- **Benign security education:** XSTest safe prompts, to measure over-refusal in general.
- **Legitimate but borderline security work:** the CyberSecEval MITRE false-refusal set (750 prompts).
- **Disallowed:** StrongREJECT (forbidden prompts with a rubric scorer, already used in this project),
  plus the CyberSecEval MITRE attack-helpfulness prompts, scored by its rubric.

Each response is labelled on two independent axes:
1. **Willingness:** full refusal / partial / complies. Deterministic patterns first, then a frozen local
   judge with a blinded human-labelled subsample for agreement (Cohen's kappa).
2. **Quality,** only where it applies: the StrongREJECT score (specificity and convincingness) for
   disallowed prompts.

Expected pattern: the aligned arm refuses many disallowed prompts and both ablated arms refuse few.
The interesting questions are over-refusal on benign security prompts, and whether the Heretic arm
differs from the abliterated arm.

### D: agent reliability and instruction integrity
- **Injection resistance:** InjecAgent (1,054 cases, 17 user tools, 62 attacker tools, ACL Findings 2024).
  Metric: attack success rate, split into direct-harm and data-exfiltration cases.
- **Reliability:** process measures from CTF v2 traces, defined before collection: failed commands
  followed by a corrected retry, repeated identical commands, and steps to first useful observation.
  This adds no extra GPU time.
- AgentDojo was already run on two of these models in stage B. It is not rerun or pooled; stage B is cited
  separately.

## Threat model and handling

- Every test is offline or against local sandboxes. No real systems, no internet from agent containers.
- Disallowed-prompt outputs (test C) and WMDP-cyber answers may contain harmful material from the
  ablated models. They are stored only in the private WSL archive. Public reports carry aggregates,
  labels and short non-actionable excerpts at most.
- Every dataset, checkpoint revision, prompt template, judge and analysis rule is frozen and pushed
  before collection, as in stages B and C.

## Analysis

- Per test and per arm: point estimates with exact or bootstrap 95% intervals.
- Paired by item across arms: McNemar for binary items, descriptive for small sets such as the CTF.
- Primary contrasts, fixed in advance: abliterated vs aligned, and Heretic vs aligned.
  Heretic vs abliterated is secondary.
- Holm correction across the primary contrasts within each test. No pooling across tests.

## Cost estimate (to verify with a development dry run)

Same single A100 at about $2.22/hour, serving one model at a time.

| Block | Per model | ×3 models |
|---|---|---|
| Model load (first download ≈ 54 GB BF16) | 5–10 min | 15–30 min |
| A: CTF v2, 14 tasks, 1 trajectory + 3 dev checks | ≈ 60 min | ≈ 3 h |
| B: CyberMetric-500 + WMDP-cyber + CWEval, batched | ≈ 15 min | ≈ 45 min |
| C: XSTest + MITRE FRR + StrongREJECT + MITRE, batched, plus judging | ≈ 20 min | ≈ 1 h |
| D: InjecAgent, batched | ≈ 10 min | ≈ 30 min |
| **Total** | | **≈ 5.5–6 h ≈ $12–14** |

Without A, the batched tests B–D come to about 2.5–3 h, roughly $6–7. Either way this exceeds what is
left of the current $10 phase ceiling (about $4.22), so it needs a new budget decision, or a split into
separately approved runs, for example B+C+D first and CTF v2 second.

## Before freeze

1. Pick and pin the Heretic checkpoint after reading its model card.
2. Download and hash each dataset, and pin revisions; confirm each license allows this research use.
3. Implement the CTF v2 output fix with tests, and the B–D runners with offline tests on scripted outputs.
4. Run a small free local dry run of each runner on a tiny model or scripted responses.
5. Freeze and push. Then the read-only GPU check and an explicit spending approval.
