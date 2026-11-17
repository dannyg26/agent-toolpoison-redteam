"""Pod-side deadline backup. Does not create pods or read keys until explicitly --arm'ed.

API: https://docs.runpod.io/api-reference-v2/pods/terminate-a-pod
Run as the FIRST pod bootstrap action, before package/model downloads. The laptop watcher
continues downloading and terminating normally. This backup does not depend on laptop Wi-Fi.
At the deadline, spending protection takes priority over an unavailable final download.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

API = "https://api.runpod.io/v2/pods/"


def deadline(created_epoch, hourly_usd, max_usd, max_minutes):
    for value in (created_epoch, hourly_usd, max_usd, max_minutes):
        if not math.isfinite(value) or value <= 0:
            raise ValueError("budget inputs must be finite and positive")
    return created_epoch + min(max_minutes * 60, max_usd / hourly_usd * 3600)


def parse_created(pod):
    # Creation is deliberately conservative: setup/waiting time is NOT excluded.
    value = pod["createdAt"]
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("pod creation time must include a timezone")
    return stamp.timestamp()


def api_request(method, pod_id, key):
    request = urllib.request.Request(API + pod_id, method=method,
                                     headers={"Authorization": "Bearer " + key})
    # Never put the key in a URL or print response bodies/exceptions containing credentials.
    with urllib.request.urlopen(request, timeout=10) as response:
        if method == "GET":
            return json.load(response)
        return response.status


def terminate(pod_id, key, request=api_request):
    try:
        status = request("DELETE", pod_id, key)
        return status in (200, 202, 204)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:  # the initial GET verified this exact pod/key pair
            return True
        print(f"termination request failed: HTTP {exc.code}; retrying", flush=True)
    except (OSError, TimeoutError, ValueError):
        print("termination request failed; retrying without exposing credentials", flush=True)
    return False


def monitor(pod_id, key, stop_at, out, *, request=api_request, sleep=time.sleep,
            wall=time.time, monotonic=time.monotonic):
    remaining = max(0.0, stop_at - wall())
    mono_stop = monotonic() + remaining
    ready = {"pod_id": pod_id, "guard_pid": os.getpid(), "deadline_epoch": stop_at,
             "deadline_utc": datetime.fromtimestamp(stop_at, timezone.utc).isoformat(),
             "api_base": API, "counts_from": "pod createdAt, including setup"}
    out.mkdir(parents=True, exist_ok=True)
    (out / "guard_ready.json").write_text(json.dumps(ready, indent=2) + "\n", encoding="utf-8")
    print(f"pod-side guard armed; remaining seconds: {remaining:.0f}", flush=True)
    while wall() < stop_at and monotonic() < mono_stop:
        left = min(stop_at - wall(), mono_stop - monotonic())
        if left <= 60:
            (out / "STOP_REQUESTED").touch()
        sleep(max(0.01, min(5, left)))
    (out / "STOP_REQUESTED").touch()
    # Continue retrying even if the runner failed or the laptop disappeared.
    while not terminate(pod_id, key, request):
        sleep(5)
    print("pod termination accepted (or pod already absent)", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=str(Path(__file__).with_name("pilot_config.json")))
    ap.add_argument("--key-file")
    ap.add_argument("--out", default="/root/out/stage_b_pilot")
    ap.add_argument("--arm", action="store_true", help="enable self-termination INSIDE this RunPod pod")
    args = ap.parse_args(argv)
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    seconds = deadline(time.time(), config["hourly_usd_including_disk"], config["maximum_compute_usd"],
                       config["maximum_session_minutes"]) - time.time()
    if not args.arm:
        print(f"DRY RUN: no API calls; maximum session {seconds / 60:.1f} minutes from pod creation")
        return 0
    pod_id = os.environ.get("RUNPOD_POD_ID", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{5,80}", pod_id):
        ap.error("RUNPOD_POD_ID is required; this tool only terminates its own pod")
    if os.name != "posix":
        ap.error("armed mode is for the Linux pod, not the laptop")
    if not args.key_file:
        ap.error("--key-file is required; never put a key in chat or command arguments")
    try:
        key_path = Path(args.key_file)
        if key_path.stat().st_mode & 0o077:
            ap.error("key file must be private: chmod 600 on the pod")
        key = key_path.read_text(encoding="utf-8").strip()
        if not key or any(c.isspace() for c in key):
            ap.error("invalid key file")
        pod = api_request("GET", pod_id, key)
        if pod.get("id") != pod_id:
            ap.error("pod identity did not match; guard not armed")
        created = parse_created(pod)
        if created > time.time() + 30:
            ap.error("pod creation time is in the future; guard not armed")
        stop_at = deadline(created, config["hourly_usd_including_disk"],
                           config["maximum_compute_usd"], config["maximum_session_minutes"])
    except (OSError, ValueError, KeyError, urllib.error.URLError):
        ap.error("could not verify pod/key/start time; no GPU setup may proceed")
    monitor(pod_id, key, stop_at, Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
