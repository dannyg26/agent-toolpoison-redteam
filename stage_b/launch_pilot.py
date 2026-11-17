"""Single-pod controller. Read-only plan by default; --launch spends the explicitly bounded budget.

The key is read from a private file, never printed or stored in the result directory. A pod-side
watchdog is embedded in the startup payload; this local controller independently downloads/terminates.
No payment, top-up, persistent volume, restart or second pod is created.
"""
from __future__ import annotations
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import stat
import tarfile
import time
import urllib.error
import urllib.request
import uuid

import pilot_tools as P
from pod_guard import parse_created, deadline

BASE = "https://api.runpod.io/v2"
GPU = "NVIDIA A100-SXM4-80GB"
IMAGE = "runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404"


def request(method, path, key, body=None):
    req = urllib.request.Request(BASE + path, method=method,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=30) as response:
        return None if response.status == 204 else json.load(response)


def package_source():
    names = set(P.FILES + ["pilot_freeze.json", "test_harness.py", "test_pilot.py", "cases.json"])
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as tar:
        for name in sorted(names):
            data = (P.HERE / name).read_bytes().replace(b"\r\n", b"\n")
            info = tarfile.TarInfo("stage_b/" + name)
            info.size, info.mode = len(data), 0o600
            tar.addfile(info, io.BytesIO(data))
    return base64.b64encode(stream.getvalue()).decode("ascii")


def download_tree(sftp, remote, local):
    local.mkdir(parents=True, exist_ok=True)
    for entry in sftp.listdir_attr(remote):
        if entry.filename in (".", "..") or "/" in entry.filename or "\\" in entry.filename:
            continue
        source, target = remote + "/" + entry.filename, local / entry.filename
        if stat.S_ISDIR(entry.st_mode):
            download_tree(sftp, source, target)
        elif stat.S_ISREG(entry.st_mode) and entry.st_size <= 100_000_000:
            if target.exists() and target.stat().st_size == entry.st_size and entry.filename != "runner.log":
                continue
            partial = target.with_name(target.name + ".partial")
            sftp.get(source, str(partial))
            partial.replace(target)


def terminate(pod_id, key):
    for _ in range(12):
        try:
            request("DELETE", "/pods/" + pod_id, key)
            return True
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return True
            print(f"termination HTTP {exc.code}; retrying", flush=True)
        except (OSError, ValueError):
            print("termination connection failure; retrying", flush=True)
        time.sleep(5)
    return False


def monitor(pod_id, key, out, private_key, initial_created, hourly, maximum_minutes):
    import paramiko
    stop_at = deadline(initial_created, hourly, 3.50, maximum_minutes)
    client = None
    last_status, last_line = None, ""
    final_download = False
    try:
        while time.time() < stop_at - 15:
            pod = request("GET", "/pods/" + pod_id, key)
            actual = float(pod.get("cost") or 0)
            if actual > hourly + 0.001:
                raise RuntimeError("pod hourly rate exceeds authorized ceiling")
            state = pod.get("status")
            if state != last_status:
                print("pod state:", state, flush=True)
                last_status = state
            direct = (pod.get("ssh") or {}).get("direct")
            if not direct:
                port = next((p for p in (pod.get("runtime") or {}).get("ports", [])
                             if p.get("private") == 22 and p.get("public") and p.get("ip")), None)
                if port:
                    direct = {"host": port["ip"], "port": port["public"], "username": "root"}
            if client is None and direct:
                try:
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(direct["host"], port=direct["port"], username=direct.get("username", "root"),
                                   pkey=private_key, allow_agent=False, look_for_keys=False,
                                   timeout=5, auth_timeout=5, banner_timeout=5)
                except (OSError, paramiko.SSHException):
                    if client:
                        client.close()
                    client = None
            if client is not None:
                try:
                    with client.open_sftp() as sftp:
                        download_tree(sftp, "/root/out/stage_b_pilot", out / "download")
                    log = out / "download/runner.log"
                    if log.exists():
                        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
                        line = lines[-1] if lines else ""
                        if line != last_line:
                            # Only progress lines, never model responses, keys or complete API objects.
                            print("progress:", line[:240], flush=True)
                            last_line = line
                    finished = out / "download/finished.json"
                    digest = out / "download/archive.sha256"
                    archive = out / "download/stage_b_pilot.tar.gz"
                    if finished.exists() and digest.exists() and archive.exists():
                        final_download = hashlib.sha256(archive.read_bytes()).hexdigest() == digest.read_text().strip()
                        if final_download:
                            print("final result archive downloaded and verified", flush=True)
                            break
                except (OSError, paramiko.SSHException):
                    client.close()
                    client = None
            if state in ("ERROR", "TERMINATED", "EXITED"):
                break
            time.sleep(10)
    finally:
        if client:
            client.close()
        stopped = terminate(pod_id, key)
        result = {"pod_id": pod_id, "terminated": stopped, "final_archive_verified": final_download,
                  "elapsed_minutes": round((time.time() - initial_created) / 60, 2),
                  "maximum_quoted_spend_before_tax": round((time.time() - initial_created) / 3600 * hourly, 3)}
        (out / "run_status.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result), flush=True)
        if not stopped:
            raise RuntimeError("termination not confirmed; pod-side guard remains the independent backup")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--launch", action="store_true")
    ap.add_argument("--key-file")
    ap.add_argument("--save-to", required=True)
    args = ap.parse_args()
    config = P.load("pilot_config.json")
    for name, digest in P.load("pilot_freeze.json")["files"].items():
        if P.sha(P.HERE / name) != digest:
            raise SystemExit("source differs from freeze: " + name)
    if not args.launch:
        print("DRY RUN: no API calls, no GPU allocated; maximum quoted session $3.33 before tax")
        return
    if not args.key_file:
        ap.error("--key-file required; never supply the key value as an argument")
    out = Path(args.save_to)
    if out.exists():
        ap.error("use a new output directory; a paid launch is never silently repeated")
    key = Path(args.key_file).read_text(encoding="utf-8").strip()
    pods = request("GET", "/pods", key)
    if (pods if isinstance(pods, list) else pods.get("pods", [])):
        raise SystemExit("existing pods found; refusing to overlap spending")
    catalog = request("GET", "/catalog/gpus", key)
    gpu = next(x for x in catalog["gpus"] if x["id"] == GPU)
    gpu_price = float(gpu["price"]["secure"])
    # 200GB ephemeral disk, $0.10/GB/month, conservatively using a 720-hour month.
    quoted_hourly = gpu_price + 200 * 0.10 / 720
    if quoted_hourly > config["hourly_usd_including_disk"]:
        raise SystemExit("current A100 plus disk quote exceeds the $2.22/hour ceiling; no pod created")
    import paramiko
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH).decode()
    private_text = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH,
                                         serialization.NoEncryption()).decode()
    pkey = paramiko.Ed25519Key(file_obj=io.StringIO(private_text))
    out.mkdir(parents=True)
    (out / "ephemeral_ssh_key").write_text(private_text, encoding="utf-8")
    name = "budget-pilot-" + uuid.uuid4().hex[:8]
    boot = "import base64,os; exec(base64.b64decode(os.environ.pop('PILOT_BOOTSTRAP_B64')))"
    payload = {"name": name, "image": IMAGE, "cloud": "SECURE", "disk": 200, "startSsh": True,
               "gpu": {"id": GPU, "count": 1, "minCudaVersion": "12.8"}, "ports": ["22/tcp"],
               "entrypoint": ["python3", "-u", "-c"], "cmd": [boot],
               "env": {"PUBLIC_KEY": public, "RUNPOD_GUARD_KEY": key, "PILOT_SOURCE_B64": package_source(),
                       "PILOT_BOOTSTRAP_B64": base64.b64encode((P.HERE / "bootstrap_pilot.py").read_bytes()).decode()}}
    print(f"creating ONE A100 SXM pod; quote ${quoted_hourly:.3f}/h; 90-minute deadline including setup", flush=True)
    before = time.time()
    pod = None
    try:
        pod = request("POST", "/pods", key, payload)  # NEVER retry a creation request blindly
    except (OSError, ValueError):
        # A timed-out create might have succeeded; discover that named pod rather than rent another.
        rows = request("GET", "/pods", key)
        rows = rows if isinstance(rows, list) else rows.get("pods", [])
        found = [x for x in rows if x.get("name") == name]
        if len(found) == 1:
            pod = found[0]
        else:
            raise RuntimeError("creation response uncertain; no second creation attempted") from None
    pod_id = pod["id"]
    (out / "pod.json").write_text(json.dumps({"id": pod_id, "name": name, "quote_hourly": quoted_hourly,
        "createdAt": pod.get("createdAt"), "launch_requested_epoch": before}, indent=2) + "\n")
    print("pod allocated:", pod_id, flush=True)
    monitor(pod_id, key, out, pkey, parse_created(pod) if pod.get("createdAt") else before,
            config["hourly_usd_including_disk"], config["maximum_session_minutes"])


if __name__ == "__main__":
    main()
