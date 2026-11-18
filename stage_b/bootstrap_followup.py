"""Framing follow-up container entrypoint (adapted from bootstrap_heldout.py, which is unchanged): arm the guard with
followup_config.json BEFORE any installation.

Differs from the frozen bootstrap_pilot.py (left unchanged) in three ways:
- it passes `--config stage_b/followup_config.json` to pod_guard.py explicitly (pod_guard's own default is the
  pilot configuration, so an omitted flag would silently give the pilot's 90-minute limit);
- it then reads the pod's createdAt through its own authenticated API request and requires the guard's armed
  deadline to equal createdAt + the follow-up cap within 5 s; otherwise it stops before any setup;
- it writes to /root/out/stage_b_followup and runs run_followup.sh.
"""
import base64
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

OUT = Path("/root/out/stage_b_followup")
REPO = Path("/root/repo")
CONFIG_REL = "stage_b/followup_config.json"


def guard_command(repo, key_file, out):
    return [sys.executable, str(repo / "stage_b/pod_guard.py"), "--arm", "--config", str(repo / CONFIG_REL),
            "--key-file", str(key_file), "--out", str(out)]


def expected_deadline(created_epoch, config):
    cap = min(config["maximum_session_minutes"] * 60,
              config["maximum_compute_usd"] / config["hourly_usd_including_disk"] * 3600)
    return created_epoch + cap


def verify_guard_deadline(ready, config, created_epoch, now, pod_id):
    """The armed deadline must equal the AUTHENTICATED pod createdAt plus the follow-up cap, within a few seconds.
    `created_epoch` comes from this bootstrap's own authenticated GET of the pod, not from the guard's file."""
    tol = config["bootstrap_deadline_tolerance_seconds"]
    if ready.get("pod_id") != pod_id:
        raise RuntimeError("guard is not watching this pod")
    want = expected_deadline(created_epoch, config)
    got = float(ready["deadline_epoch"])
    if abs(got - want) > tol:
        raise RuntimeError(f"guard deadline differs from createdAt + held-out cap by {(got - want) / 60:.2f} min")
    if not created_epoch - 60 <= now < got:
        raise RuntimeError("clock or creation time inconsistent with the guard deadline")
    return got - now


def authenticated_created(pod_id, key):
    sys.path.insert(0, str(REPO / "stage_b"))
    import pod_guard
    pod = pod_guard.api_request("GET", pod_id, key)
    if pod.get("id") != pod_id:
        raise RuntimeError("pod identity did not match")
    return pod_guard.parse_created(pod)


def main():
    os.umask(0o077)
    OUT.mkdir(parents=True, exist_ok=True)
    REPO.mkdir(parents=True, exist_ok=True)
    payload = base64.b64decode(os.environ.pop("FOLLOWUP_SOURCE_B64"))
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        tar.extractall(REPO, filter="data")
    config = json.loads((REPO / CONFIG_REL).read_text(encoding="utf-8"))
    if config.get("study") != "followup":
        raise RuntimeError("follow-up configuration missing; no setup started")
    private = Path("/root/.followup_private")
    private.mkdir(mode=0o700, exist_ok=True)
    key_file = private / "pods.key"
    key_file.write_text(os.environ.pop("RUNPOD_GUARD_KEY"), encoding="utf-8")
    key_file.chmod(0o600)
    with (OUT / "guard.log").open("ab", buffering=0) as log:
        guard = subprocess.Popen(guard_command(REPO, key_file, OUT), stdout=log, stderr=log, start_new_session=True)
    for _ in range(60):
        if guard.poll() is not None:
            raise RuntimeError("pod guard could not arm; local watcher must terminate")
        if (OUT / "guard_ready.json").exists():
            break
        time.sleep(1)
    else:
        raise RuntimeError("pod guard did not become ready; no benchmark setup started")
    ready = json.loads((OUT / "guard_ready.json").read_text(encoding="utf-8"))
    pod_id = os.environ.get("RUNPOD_POD_ID", "")
    created = authenticated_created(pod_id, key_file.read_text(encoding="utf-8").strip())
    remaining = verify_guard_deadline(ready, config, created, time.time(), pod_id)
    (OUT / "guard_verified.json").write_text(json.dumps({
        "remaining_minutes_at_boot": round(remaining / 60, 2), "config": CONFIG_REL,
        "deadline_minus_created_minutes": round((float(ready["deadline_epoch"]) - created) / 60, 3)}) + "\n",
        encoding="utf-8")
    print("GUARD_ARMED_AND_VERIFIED", flush=True)
    ssh_dir = Path("/root/.ssh")
    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    (ssh_dir / "authorized_keys").write_text(os.environ.pop("PUBLIC_KEY") + "\n", encoding="utf-8")
    (ssh_dir / "authorized_keys").chmod(0o600)
    Path("/run/sshd").mkdir(exist_ok=True)
    subprocess.run(["ssh-keygen", "-A"], check=True, stdout=subprocess.DEVNULL)
    ssh = subprocess.Popen(["/usr/sbin/sshd", "-D", "-o", "PasswordAuthentication=no", "-o",
                            "PermitRootLogin=prohibit-password"], start_new_session=True)
    os.environ["FOLLOWUP_GUARD_PID"] = str(guard.pid)
    os.environ["REPO"], os.environ["OUT"] = str(REPO), str(OUT)
    code = subprocess.call(["bash", str(REPO / "stage_b/run_followup.sh"), "--run"])
    print(f"RUNNER_EXIT={code}; waiting for result download or pod deadline", flush=True)
    while guard.poll() is None:          # stay reachable for the laptop; the guard outlives runner failure
        time.sleep(5)
    ssh.terminate()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
