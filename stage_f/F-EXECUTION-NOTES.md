# Stage F execution notes

Unfrozen log of how the frozen stage F protocol (`F-PROTOCOL.md`, freeze commit `16b6913`, pushed
2026-11-20 before any stage F model call) was executed. The freeze excludes files named `F-EXECUTION*`.
All times are UTC on 2026-11-20. Costs are the launcher's quoted upper bound (elapsed time × quoted rate,
before tax).

- **Stale status line in the frozen protocol (R6-17).** Line 3 of `F-PROTOCOL.md` still reads "Status:
  draft for the review loop ... Nothing frozen, rented or run." That line is stale. The protocol was frozen
  in commit `16b6913`, and the file is left unchanged because editing it would break the freeze hash.

## F1 (one pod, session `f1a`)

- Approved in chat; preflight showed no pods running and a $2.2178/h quote. Cap $3.43.
- Pod `rhq1gpjx3q48ek`. Guard armed first. Install 17:06:40–17:09:20 (no retry needed).
- Arms in the frozen order:

  | Arm | Generate | Thinking closed | Judge |
  |---|---|---|---|
  | aligned | 17:09:40–17:19:13 | 310/313 | done 17:19:44 |
  | abliterated | 17:20:05–17:43:28 | 124/313, **ALERT** (< 50%) | done 17:43:45 |
  | heretic | 17:44:15–18:05:43 | 165/313 | done 18:06:00 |

- `ALL_DONE` and `DRIVER_EXIT 0` at 18:06:01. All 15 pod files were fetched with matching SHA-256 markers.
  The pod was terminated. Elapsed 60.46 min, quoted bound **$2.235**.
- The abliterated ALERT triggered the pre-registered fallback-split sensitivity analysis for all arms. It
  gave the same willingness counts and scores as the primary rule for every arm, so no answer was
  recovered: the unclosed answers were thinking that ran to the 4,096-token limit (abliterated 239 and
  heretic 202 length-capped, against 8 for aligned). Added in review cycle 6: a cross-tab of the private
  finish reasons confirms that every no-answer prompt (aligned 3, abliterated 189, heretic 148) was
  length-capped with its thinking still open (`results/f_derived_aggregates.json`, counts only).
- The summary (`results/f1_summary.json`) was produced by the frozen `analyze_f.py f1` and committed as
  `75d896d`.

## F2 (one pod per arm)

- **Two aborted launch attempts, no pod created, nothing spent.** The first aligned attempt ran as the
  wrong WSL user and stopped with a permission error while reading the frozen F1 manifest, inside the
  freeze check and before any pod request. The second, run as root, stopped at the freeze check's
  "HEAD must be on a remote branch" rule because the F1 results commit had not been pushed. After the
  user approved the push of `75d896d`, the third attempt launched. The frozen files were unchanged
  throughout, and `freeze_f.py check` verified.
- The pre-registered 15-minute install operator rule was **not needed**. Every install finished in under
  3 minutes, and there was no manual intervention in any F2 pod.

  | Arm | Pod | Install | Serving | Trials | Elapsed | Quoted bound |
  |---|---|---|---|---|---|---|
  | aligned | `eoufuseil19sq4` | 20:23:15–20:25:55 | 20:31:10 | 14/14 observed | 15.85 min | $0.586 |
  | abliterated | `do61srf21p3k6k` | 21:21:26–21:24:12 | 21:32:21 | 14/14 observed | 32.34 min | $1.195 |
  | heretic | `cv2u8ea8myy6cw` | 21:55:00–21:57:32 | 22:05:48 | 14/14 observed | 39.19 min | $1.449 |

- Every pod was confirmed terminated. There were no infrastructure failures and no missing or unplanned
  trials.
- The summary (`results/f2_summary.json`) was produced by the frozen `analyze_f.py f2`. Before it was
  committed, it was checked to contain no flag-like strings.

## Hand-label sheet: location deviation

- `make_label_sheet.py` built the sheet from all 42 observed F2 trials, with no flag-like strings in it.
- The protocol says the sheet and key live under `/home/capstone-study/stage_f/private/`. That directory
  is root-only inside WSL, so the author could not easily open the sheet there. It was instead written to
  a private folder in the author's Windows home directory, which is still **outside the repository**.
- The key (`label_key.json`) sits in the same folder. The author is to label without opening it, per the
  protocol. This is a minor procedural deviation, disclosed here.
- **Sync and backup check (review cycle 6, R6-16).** The folder was checked, without opening the sheet, against
  every OneDrive account folder registered for the Windows user (personal and work or school) and against the
  OneDrive environment variables. It lies inside none of them, and it has no cloud-file attributes. The
  Desktop and Documents folders are redirected into OneDrive, but the sheet's folder is not under either.
  Windows File History is not configured. Other backup software was not checked. So the sheet is not
  cloud-synced by OneDrive.
- After labelling and `analyze_f.py f2labels`, the sheet and key are to be moved back into the root-only
  private directory, or deleted, so that no copy of the model text stays in the Windows home directory.
- At the time of writing, the labels have not been entered and `analyze_f.py f2labels` has not been run.

## Spend

Stage F quoted bound: F1 $2.235 + F2 $3.230 = **$5.465** before tax.
