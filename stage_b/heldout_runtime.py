"""Held-out deadline-aware execution around the UNCHANGED harness.py (the pilot's frozen files stay untouched).

Soft stop = guard deadline - soft_stop_seconds (300 s). Two layers:

1. ENFORCED elapsed-time bound (the guarantee): `supervise` runs each harness phase as a CHILD PROCESS and
   kills it (process group; SIGTERM, then SIGKILL after 5 s) at soft stop + grace (30 s), whatever the child
   is doing. The parent runner survives to write the planned-inventory report and the archive. Records the
   child completed are kept (one JSONL line per finished unit); units in flight or never started have no
   record and are reported as incomplete/unknown. A kill is logged to supervisor_events.jsonl.
2. Graceful best effort inside the child (`run`): after the soft stop, or once STOP_REQUESTED exists, no
   request and no retry starts (DeadlineStop, not retryable), and each request's SDK timeout is capped at the
   time left. NOTE: an SDK/HTTPX timeout bounds each network operation (e.g. the wait for the next chunk),
   not the total response time, so a slowly streamed response can outlive it. That is why layer 1 exists.

    python stage_b/heldout_runtime.py timer --ready <guard_ready.json> --stop-file <STOP_REQUESTED> --soft-stop-seconds 300
    python stage_b/heldout_runtime.py soft-stop-epoch --ready <guard_ready.json> --soft-stop-seconds 300
    python stage_b/heldout_runtime.py supervise --ready <guard_ready.json> --soft-stop-seconds 300 --grace-seconds 30 \
        --events <supervisor_events.jsonl> -- <harness.py arguments>
    python stage_b/heldout_runtime.py run --ready <guard_ready.json> --soft-stop-seconds 300 -- <harness.py arguments>

Retries keep the harness's semantics (identical request, at most 3 retries after a connection error, timeout,
HTTP 5xx or 429, backoff 5/10/20 s) but never start, or sleep, past the soft stop.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

KILLED_EXIT = 124
TERM_WAIT_SECONDS = 5

HERE = Path(__file__).resolve().parent
RETRY_TRIES = 4                  # one request + 3 retries, as in harness._with_retries
BACKOFF = (5, 10, 20)


class DeadlineStop(Exception):
    """Raised instead of starting a request or retry after the soft stop. Recorded as a `deadline` outcome."""


def soft_stop_epoch(ready_path, soft_stop_seconds):
    ready = json.loads(Path(ready_path).read_text(encoding="utf-8"))
    return float(ready["deadline_epoch"]) - float(soft_stop_seconds)


class Deadline:
    def __init__(self, soft_stop_at, stop_file=None, clock=time.time, sleep=time.sleep):
        self.soft_stop_at, self.stop_file, self.clock, self.sleep = soft_stop_at, stop_file, clock, sleep

    def stopped(self):
        return self.clock() >= self.soft_stop_at or bool(self.stop_file and Path(self.stop_file).exists())

    def remaining(self):
        return self.soft_stop_at - self.clock()


def deadline_retries(deadline):
    """Drop-in for harness._with_retries that respects the soft stop."""
    import openai
    retryable = (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError, openai.RateLimitError)

    def with_retries(fn, tries=RETRY_TRIES):
        for i in range(tries):
            if deadline.stopped():
                raise DeadlineStop("soft stop reached before request start")
            try:
                return fn()
            except retryable:
                if i == tries - 1:
                    raise
                wait = BACKOFF[min(i, len(BACKOFF) - 1)]
                if deadline.stopped() or deadline.remaining() <= wait:
                    raise DeadlineStop("soft stop reached; no retry started") from None
                deadline.sleep(wait)
    return with_retries


class _Completions:
    def __init__(self, real, deadline, max_timeout):
        self.real, self.deadline, self.max_timeout = real, deadline, max_timeout

    def create(self, **kwargs):
        if self.deadline.stopped():
            raise DeadlineStop("soft stop reached before request start")
        left = self.deadline.remaining()
        if left <= 1:
            raise DeadlineStop("no time left before the soft stop")
        # Best effort only: this bounds each network operation, not total response time (see module docstring).
        kwargs["timeout"] = min(self.max_timeout, left)
        return self.real.chat.completions.create(**kwargs)


class DeadlineClient:
    """Wraps an OpenAI client so that `.chat.completions.create` cannot START after the soft stop, and caps each
    request's SDK timeout at the time left. It does NOT bound total response time; `supervise` does."""

    def __init__(self, real, deadline, max_timeout):
        self.chat = type("Chat", (), {})()
        self.chat.completions = _Completions(real, deadline, max_timeout)


def run_harness(argv, deadline, client_factory=None):
    """Build the harness's own TargetLLM / Attacker on deadline-aware clients and call harness.main."""
    sys.path.insert(0, str(HERE))
    import harness as H
    import openai
    ap = argparse.ArgumentParser(add_help=False)
    for flag in ("--target-url", "--target-model", "--attacker-url", "--attacker-model"):
        ap.add_argument(flag)
    for flag in ("--target-max-tokens", "--attacker-max-tokens", "--target-thinking-budget",
                 "--attacker-thinking-budget"):
        ap.add_argument(flag, type=int)
    ap.add_argument("--request-timeout", type=float, default=900)
    known, _ = ap.parse_known_args(argv)
    known.target_url = known.target_url or "http://127.0.0.1:8500/v1"
    known.attacker_url = known.attacker_url or "http://127.0.0.1:8600/v1"
    factory = client_factory or (lambda url: openai.OpenAI(base_url=url, api_key="EMPTY", max_retries=0,
                                                           timeout=known.request_timeout))
    H._with_retries = deadline_retries(deadline)       # module-level name looked up at call time
    tclient = DeadlineClient(factory(known.target_url), deadline, known.request_timeout)
    make_llm = lambda: H.TargetLLM(tclient, known.target_model, max_tokens=known.target_max_tokens or 8192,
                                   thinking_token_budget=known.target_thinking_budget)
    attacker = None
    if known.attacker_model:
        aclient = DeadlineClient(factory(known.attacker_url), deadline, known.request_timeout)
        attacker = H.Attacker(aclient, known.attacker_model, max_tokens=known.attacker_max_tokens or 8192,
                              thinking_token_budget=known.attacker_thinking_budget)
    return H.main(argv, attacker=attacker, make_llm=make_llm)


def _spawn(argv):
    if os.name == "posix":
        return subprocess.Popen(argv, start_new_session=True)
    return subprocess.Popen(argv, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)


def _stop_tree(proc, sig):
    try:
        if os.name == "posix":
            os.killpg(proc.pid, sig)
        elif sig == signal.SIGTERM:
            proc.terminate()
        else:
            proc.kill()
    except (ProcessLookupError, PermissionError, OSError):
        pass


def supervise(child_argv, kill_at, events_path=None, label="", term_wait=TERM_WAIT_SECONDS, poll=0.2):
    """Run child_argv; if it is still running at kill_at (wall clock), terminate it and return KILLED_EXIT.
    Returns (exit_code, killed)."""
    def event(**kw):
        if events_path:
            with open(events_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"label": label, "time": time.time(), **kw}) + "\n")
    if time.time() >= kill_at:
        event(started=False, killed=False, reason="past supervisor cutoff before start")
        return KILLED_EXIT, True
    proc = _spawn(child_argv)
    while proc.poll() is None and time.time() < kill_at:
        time.sleep(max(0.01, min(poll, kill_at - time.time())))
    if proc.poll() is not None:
        return proc.returncode, False
    _stop_tree(proc, signal.SIGTERM)
    try:
        proc.wait(timeout=term_wait)
    except subprocess.TimeoutExpired:
        _stop_tree(proc, getattr(signal, "SIGKILL", signal.SIGTERM))
        proc.wait()
    event(started=True, killed=True, killed_at=time.time(), cutoff=kill_at)
    return KILLED_EXIT, True


def timer(soft_stop_at, stop_file, clock=time.time, sleep=time.sleep):
    while clock() < soft_stop_at:
        sleep(max(0.05, min(5.0, soft_stop_at - clock())))
    Path(stop_file).touch()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    harness_args = []
    if "--" in argv:
        i = argv.index("--")
        argv, harness_args = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["timer", "soft-stop-epoch", "run", "supervise"])
    ap.add_argument("--ready", required=True)
    ap.add_argument("--soft-stop-seconds", type=float, required=True)
    ap.add_argument("--stop-file")
    ap.add_argument("--grace-seconds", type=float, default=30)
    ap.add_argument("--events")
    args = ap.parse_args(argv)
    at = soft_stop_epoch(args.ready, args.soft_stop_seconds)
    if args.action == "soft-stop-epoch":
        print(int(at))
        return 0
    if args.action == "supervise":
        child = [sys.executable, str(Path(__file__).resolve()), "run", "--ready", args.ready,
                 "--soft-stop-seconds", str(args.soft_stop_seconds), "--", *harness_args]
        out = harness_args[harness_args.index("--out") + 1] if "--out" in harness_args else ""
        code, killed = supervise(child, at + args.grace_seconds, args.events, label=out)
        if killed:
            print(f"SUPERVISOR: harness phase stopped at soft stop + {args.grace_seconds:g} s ({out})", flush=True)
        return code
    if args.action == "timer":
        if not args.stop_file:
            ap.error("--stop-file is required")
        timer(at, args.stop_file)
        return 0
    stop_file = None
    if "--stop-file" in harness_args:
        stop_file = harness_args[harness_args.index("--stop-file") + 1]
    return run_harness(harness_args, Deadline(at, stop_file))


if __name__ == "__main__":
    raise SystemExit(main())
