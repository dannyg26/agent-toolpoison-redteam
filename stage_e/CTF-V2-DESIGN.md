# CTF v2 design draft (stage E, run 2)

**Status: draft for the review loop. Nothing frozen, built, rented or spent.** Stage C results stand
alone and are never pooled with v2.

## Why v2

Stage C (14 CTFTiny web/pwn tasks, 240 s and 24 tool calls, one attempt) produced a floor effect:
1/14 solved by the uncensored arm and 2/14 by the aligned arm. Two design limits drove it:

1. **Wall-clock budget spent on generation.** In trials that hit the time limit, model generation used
   about 75–95% of the 240 s (REVIEW-001), so the budget mostly measured serving speed.
2. **Binary output filled the context.** In 7 of 22 pwn trials, one `cat` of a binary became 44–151 KB
   of JSON-escaped tool text, which ended the trial after 2 calls.

## Proposed changes

| Item | Stage C | v2 proposal |
|---|---|---|
| Arms | uncensored, aligned | aligned, abliterated (Huihui), heretic (jakejb53), all at pinned revisions |
| Primary budget | 240 s wall clock | **50 tool calls and 64k generated tokens per trajectory**; 15-minute wall-clock safety cap, reported separately |
| Tool output | raw bytes, up to 32 KB | **printable-safe output**: non-printable bytes replaced by a `\xNN` summary; at most 8 KB shown to the model per call, with head and tail kept; the full output kept in the private trace |
| Context | 32k | 32k; when exceeded, the oldest tool outputs are elided with a fixed marker (rule fixed before collection) |
| Attempts | 1 | 1 per task per arm in the primary analysis; a second attempt only if the budget allows (pre-registered as secondary) |
| Concurrency | 1 trial at a time | **4 trials at once** on one vLLM server and four sandboxes on the laptop; every arm sees the same concurrency |
| Results | written per trial | the same, and fetched incrementally; no end-of-arm-only outputs |
| Pod scope | one pod for everything | **one arm per pod**, so a slow arm cannot cost another arm its data |
| Benchmark | CTFTiny 14 | CTFTiny 14 (comparable to stage C); **Cybench** as a candidate addition, with subtask partial credit (see stage_d/EXPANDED-STUDY-PLAN.md for its open issues) |

## Fairness under concurrency

Time-based limits are unfair when trials share a GPU, because per-trial speed then depends on other
trials. The primary limits are therefore counts (tool calls, generated tokens). The wall-clock cap only
guards cost; a trial that reaches it is labelled `time_cap` and reported separately. All arms run with
the same concurrency (4), the same task order, and seeds from SHA-256 of the task ID.

## Cost estimate (from measured stage C and run 1 speeds; to be confirmed in development)

About 10–15 minutes per trial of generation at 50 steps. With 14 tasks at 4 concurrent, that is about
1.5–2 h per arm plus about 15 min of setup: about **$4.50–5 per arm**, or about $15 for three arms
on three separately approved pods.

## Open questions for the review loop

1. Does printable-safe output change task difficulty? Some pwn tasks need raw bytes. The model can still
   run `xxd` or `python3` to inspect them, since only the display is sanitised.
2. Is a 64k-token budget the right level? Calibrate on the three development tasks only.
3. Adding Cybench: needs contamination handling (static flags, public writeups), isolation rework and cost.
4. Should development checks run per arm on each pod? (Yes, as in stage C.)
