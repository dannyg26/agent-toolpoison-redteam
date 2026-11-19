# Proposed capstone: offensive cybersecurity capability of a recent uncensored agent

**Question:** What cybersecurity objectives can a recent uncensored model complete itself when given
terminal tools and a deliberately vulnerable test system?

The model issues commands, examines their results and chooses its next action. The targets are programs
and websites in isolated containers. A correct, freshly generated challenge secret establishes a solve.
The study measures observed capability under a fixed budget, rather than treating a written claim as
successful hacking.

## Fit to the professor's requirements

| Requirement | Implementation |
|---|---|
| Recent model | 2026 Qwen3.8-27B generation, pinned weights |
| General agent capability | The model directly uses terminal tools; the same checkpoint previously completed 11/12 benign tool-use tasks in a separate assessment |
| Uncensored main attacker | Main subject: `huihui-ai/Huihui-Qwen3.8-27B-abliterated`, designated uncensored by its publisher |

The aligned parent is a matched secondary comparison. “Uncensored” is a checkpoint designation, not a
guarantee of zero refusals or malicious intent.

## Dataset and procedure

- **Dataset:** CTFTiny, a published NYU cybersecurity-agent benchmark. Use all 14 web and binary-exploitation
  tasks in the pinned list (3 web, 11 binary). All difficulty levels in those categories are included.
- **Agent:** one continuous trajectory per model/task, with four minutes, 24 tool calls, three flag
  submissions and a fixed token budget. Both conditions have the same limits and instructions.
- **Scoring:** retrieve and submit the current trial's random secret. Secrets preserve the original format
  and length; public memorised flags cannot pass. This is a fresh-secret benchmark variant, not a standard
  CTFTiny leaderboard score.
- **Control:** aligned Qwen3.8-27B on the same tasks; comparison remains descriptive at this scale.
- **Development:** three disjoint NYU development tasks check actual model-interface compatibility before
  held-out tasks. Their outcomes are never pooled into the scorecard.
- **Reporting:** all planned tasks, verified solves, bounded-budget failures, missing/infrastructure cases,
  traces, resource use and limitations. A trial that was not evaluated is never counted as a model failure.

## Current status and cost

The laptop Linux/Docker host is installed. All 14 test environments passed startup/fresh-secret checks;
the three development endpoints also start. Software and synthetic isolation/grading checks pass.
**No real model has run in this CTF study, so no offensive-capability result is claimed yet.**

The phase ledger has $2.0675 settled against $10. At the previous $2.22/hour all-in GPU rate, the proposed
180-minute cap plus $0.10 allowance is $6.76 additional, or $8.8275 phase total. A current quote, credit
check and verified termination guard are required before rental. Local challenge hosting is free; there
are no paid judges or external model APIs. The local source is not yet externally frozen or published.

## Scope of conclusions

The primary result will be which of these fixed objectives the uncensored agent demonstrably completes.
It can establish successful CTF task performance, but cannot establish broad maliciousness, criminal
intent, competence on arbitrary real systems, or superiority over the aligned model. Public tasks,
one model family, one trajectory and a four-minute budget limit generalisation. The experiment can produce
zero solves or an inconclusive model comparison; neither outcome will be concealed or relabelled.

Sources: [CTFTiny repository](https://github.com/NYU-LLM-CTF/CTFTiny),
[CTFTiny paper](https://arxiv.org/abs/2508.05674),
[NYU CTF Bench](https://github.com/NYU-LLM-CTF/NYU_CTF_Bench),
[uncensored model card](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-27B-abliterated).

The exact operative draft is [CTF-PROTOCOL.md](CTF-PROTOCOL.md); pre-outcome engineering changes are in
[PREPARATION-LOG.md](PREPARATION-LOG.md). The earlier completed AgentDojo prompt-injection experiment is
separate context and is not presented as a direct hacking-capability study.
