"""Framing follow-up runtime: the accepted held-out runtime (heldout_runtime.py, unchanged) plus ONE change, the
attacker system prompt selected by --framing (followup_prompts.variants). harness.py stays unchanged; the variant
is set on the imported module before harness.main runs, and checked against the frozen text.

    python stage_b/followup_runtime.py supervise --framing neutral --ready <guard_ready.json> --soft-stop-seconds 300 \
        --grace-seconds 30 --events <supervisor_events.jsonl> -- <harness.py arguments>
    python stage_b/followup_runtime.py run --framing neutral --ready ... -- <harness.py arguments>
    (timer / soft-stop-epoch: use heldout_runtime.py directly)

The attacker label must end with "-<framing>" (e.g. aligned-neutral) so results land in separate files, and a
framing.json record is written beside the results.
"""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import heldout_runtime as R  # noqa: E402
import followup_prompts as FP  # noqa: E402


def apply_framing(harness_module, framing):
    v = FP.variants(harness_module)                 # computed from the frozen, unmodified prompt
    if framing not in v:
        raise SystemExit(f"unknown framing {framing}")
    harness_module.ATTACKER_SYSTEM = v[framing]
    return v[framing]


def _arg(args, flag):
    return args[args.index(flag) + 1] if flag in args else None


def run(framing, ready, soft_stop_seconds, harness_args):
    label = _arg(harness_args, "--attacker-label")
    if _arg(harness_args, "--condition") in ("adaptive", "nonadaptive"):
        if not label or not label.endswith("-" + framing):
            raise SystemExit("--attacker-label must end with -<framing>")
    import harness as H
    prompt = apply_framing(H, framing)
    out = Path(_arg(harness_args, "--out"))
    out.mkdir(parents=True, exist_ok=True)
    rec = out / f"framing__{label or 'none'}.json"
    rec.write_text(json.dumps({"framing": framing, "attacker_label": label,
                               "system_prompt_sha256": __import__("hashlib").sha256(prompt.encode()).hexdigest()})
                   + "\n", encoding="utf-8")
    stop_file = _arg(harness_args, "--stop-file")
    return R.run_harness(harness_args, R.Deadline(R.soft_stop_epoch(ready, soft_stop_seconds), stop_file))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    harness_args = []
    if "--" in argv:
        i = argv.index("--")
        argv, harness_args = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["run", "supervise"])
    ap.add_argument("--framing", required=True, choices=["authorized", "neutral"])
    ap.add_argument("--ready", required=True)
    ap.add_argument("--soft-stop-seconds", type=float, required=True)
    ap.add_argument("--grace-seconds", type=float, default=30)
    ap.add_argument("--events")
    args = ap.parse_args(argv)
    if args.action == "run":
        return run(args.framing, args.ready, args.soft_stop_seconds, harness_args)
    at = R.soft_stop_epoch(args.ready, args.soft_stop_seconds)
    child = [sys.executable, str(Path(__file__).resolve()), "run", "--framing", args.framing, "--ready", args.ready,
             "--soft-stop-seconds", str(args.soft_stop_seconds), "--", *harness_args]
    out = _arg(harness_args, "--out") or ""
    code, killed = R.supervise(child, at + args.grace_seconds, args.events, label=f"{out} [{args.framing}]")
    if killed:
        print(f"SUPERVISOR: phase stopped at soft stop + {args.grace_seconds:g} s ({out}, {args.framing})", flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
