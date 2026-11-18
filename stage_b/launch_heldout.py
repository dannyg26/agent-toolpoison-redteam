"""Held-out single-pod controller. Dry run by default; --check-access is read-only; --launch spends.

Reuses the frozen pilot controller's HTTP, download and termination helpers (launch_pilot.py is unchanged).
Every limit comes from heldout_config.json through heldout_tools.load_config, which refuses the pilot config.
The local deadline is pod_guard.deadline() on the SAME pod createdAt and the SAME config fields the pod-side
guard uses, so both timers stop at the same moment (the guard additionally requests a stop 60 s earlier).

Keys are read from private files and never printed. Two keys are used:
- --key-file: the pod-scoped REST key (pods list, catalog, create, delete; also handed to the pod guard);
- --balance-key-file: used ONLY for the read-only GraphQL balance query (the pod-scoped key cannot read it).
No payment, top-up, persistent volume, restart or second pod is ever created.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import time
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import heldout_tools as T  # noqa: E402
from launch_pilot import GPU, IMAGE, request, download_tree, terminate  # noqa: E402
from pod_guard import deadline, parse_created  # noqa: E402

REMOTE_OUT = "/root/out/stage_b_heldout"
ARCHIVE = "stage_b_heldout.tar.gz"


def local_deadline(created_epoch, config):
    return deadline(created_epoch, config["hourly_usd_including_disk"], config["maximum_compute_usd"],
                    config["maximum_session_minutes"])


def quoted_hourly(gpu_price, config):
    return gpu_price + config["disk_gb"] * 0.10 / 720         # temporary disk, $0.10/GB/month, 720-h month


def read_balance(balance_key):
    body = json.dumps({"query": "query { myself { clientBalance currentSpendPerHr } }"}).encode()
    req = urllib.request.Request("https://api.runpod.io/graphql", data=body, method="POST",
                                 headers={"Authorization": "Bearer " + balance_key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as response:
        me = json.load(response)["data"]["myself"]
    return float(me["clientBalance"]), float(me["currentSpendPerHr"])


def package_source():
    names = sorted(set(T.FILES + ["heldout_freeze.json"]))
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as tar:
        for name in names:
            data = (T.HERE / name).read_bytes().replace(b"\r\n", b"\n")
            info = tarfile.TarInfo("stage_b/" + name)
            info.size, info.mode = len(data), 0o600
            tar.addfile(info, io.BytesIO(data))
    return base64.b64encode(stream.getvalue()).decode("ascii")


def preflight(key, balance_key, config):
    """Read-only: no pods exist, price within the ceiling, balance covers the cap plus margin."""
    pods = request("GET", "/pods", key)
    rows = pods if isinstance(pods, list) else pods.get("pods", [])
    catalog = request("GET", "/catalog/gpus", key)
    gpu = next(x for x in catalog["gpus"] if x["id"] == config["gpu"])
    hourly = quoted_hourly(float(gpu["price"]["secure"]), config)
    balance, spend = read_balance(balance_key)
    result = {"existing_pods": len(rows), "secure_gpu_price": gpu["price"]["secure"],
              "quoted_hourly_with_disk": round(hourly, 4), "hourly_ceiling": config["hourly_usd_including_disk"],
              "balance_usd": round(balance, 4), "current_spend_per_hour": spend,
              "minimum_balance_before_launch": config["minimum_balance_before_launch_usd"]}
    result["ok"] = (not rows and hourly <= config["hourly_usd_including_disk"] and spend == 0
                    and balance >= config["minimum_balance_before_launch_usd"])
    return result


def local_report(out):
    """Planned-inventory report from whatever was downloaded, even if the pod never reached its own report.
    Needs no agentdojo: analyze_heldout reads only the JSONL results and the frozen case files."""
    try:
        import analyze_heldout as A
        rep = A.report(out / "download")
        (out / "heldout_summary_local.json").write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
        print("local planned-inventory report:", rep["primary"]["verdict"][:120],
              f"(complete pairs {rep['primary']['complete_pairs']}/32; diagnostics {len(rep['file_diagnostics'])})",
              flush=True)
    except Exception as exc:                 # never mask the termination result
        print(f"local report failed: {type(exc).__name__}; run analyze_heldout.py report --download "
              f"{out / 'download'}", flush=True)


def monitor(pod_id, key, out, private_key, created, config):
    import paramiko
    stop_at = local_deadline(created, config)
    hourly = config["hourly_usd_including_disk"]
    client, last_status, last_line, final_download = None, None, "", False
    try:
        while time.time() < stop_at - 15:
            pod = request("GET", "/pods/" + pod_id, key)
            if float(pod.get("cost") or 0) > hourly + 0.001:
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
                        download_tree(sftp, REMOTE_OUT, out / "download")
                    log = out / "download/runner.log"
                    if log.exists():
                        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
                        line = lines[-1] if lines else ""
                        if line != last_line:
                            print("progress:", line[:240], flush=True)    # progress lines only
                            last_line = line
                    finished, digest = out / "download/finished.json", out / "download/archive.sha256"
                    archive = out / "download" / ARCHIVE
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
                  "elapsed_minutes": round((time.time() - created) / 60, 2),
                  "maximum_quoted_spend_before_tax": round((time.time() - created) / 3600 * hourly, 3)}
        (out / "run_status.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result), flush=True)
        local_report(out)
        if not stopped:
            raise RuntimeError("termination not confirmed; pod-side guard remains the independent backup")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check-access", action="store_true", help="read-only API checks; never creates a pod")
    mode.add_argument("--launch", action="store_true")
    ap.add_argument("--key-file")
    ap.add_argument("--balance-key-file")
    ap.add_argument("--save-to")
    args = ap.parse_args()
    config = T.load_config()
    scenarios, checks = T.worksheet(config)
    plan = {"hard_cap_minutes_from_pod_creation": config["maximum_session_minutes"],
            "cap_usd_at_quoted_rate": checks["cap_usd_at_quoted_rate"],
            "conservative_minutes": scenarios[1]["total_minutes"], "normal_minutes": scenarios[0]["total_minutes"],
            "both_timers": "pod_guard.deadline(createdAt, hourly, maximum_compute_usd, maximum_session_minutes)"}
    if not (args.check_access or args.launch):
        print("DRY RUN: no API calls, no GPU allocated")
        print(json.dumps(plan, indent=1))
        return
    if not (args.key_file and args.balance_key_file):
        ap.error("--key-file and --balance-key-file are required; never pass key values as arguments")
    key = Path(args.key_file).expanduser().read_text(encoding="utf-8").strip()
    balance_key = Path(args.balance_key_file).expanduser().read_text(encoding="utf-8").strip()
    check = preflight(key, balance_key, config)
    print(json.dumps(check, indent=1))
    if args.check_access:
        print("read-only access check complete; no pod created")
        return
    if not check["ok"]:
        raise SystemExit("preflight failed (pods exist, price above ceiling, spending, or balance below minimum)")
    if not (T.HERE / "heldout_freeze.json").exists():
        raise SystemExit("heldout_freeze.json is missing; freeze, commit and push before any launch")
    freeze = T.load("heldout_freeze.json")["files"]
    bad = [f for f, d in freeze.items() if T.sha(T.HERE / f) != d] + sorted(set(T.FILES) - set(freeze))
    if bad:
        raise SystemExit(f"source differs from held-out freeze: {bad}")
    if not args.save_to or Path(args.save_to).exists():
        ap.error("--save-to must be a NEW directory; a paid launch is never silently repeated")
    import paramiko
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH).decode()
    private_text = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH,
                                         serialization.NoEncryption()).decode()
    pkey = paramiko.Ed25519Key(file_obj=io.StringIO(private_text))
    out = Path(args.save_to)
    out.mkdir(parents=True)
    (out / "ephemeral_ssh_key").write_text(private_text, encoding="utf-8")
    name = "heldout-" + uuid.uuid4().hex[:8]
    boot = "import base64,os; exec(base64.b64decode(os.environ.pop('HELDOUT_BOOTSTRAP_B64')))"
    payload = {"name": name, "image": IMAGE, "cloud": config["cloud"], "disk": config["disk_gb"], "startSsh": True,
               "gpu": {"id": config["gpu"], "count": 1, "minCudaVersion": "12.8"}, "ports": ["22/tcp"],
               "entrypoint": ["python3", "-u", "-c"], "cmd": [boot],
               "env": {"PUBLIC_KEY": public, "RUNPOD_GUARD_KEY": key, "HELDOUT_SOURCE_B64": package_source(),
                       "HELDOUT_BOOTSTRAP_B64": base64.b64encode((T.HERE / "bootstrap_heldout.py").read_bytes()).decode()}}
    print(f"creating ONE {config['gpu']} pod; {config['maximum_session_minutes']}-minute deadline from creation",
          flush=True)
    before = time.time()
    try:
        pod = request("POST", "/pods", key, payload)        # never retried blindly
    except urllib.error.HTTPError as exc:
        (out / "allocation_error.json").write_text(json.dumps({"status": exc.code}) + "\n")
        raise SystemExit(f"RunPod refused allocation: HTTP {exc.code}; no blind retry") from None
    except (OSError, ValueError):
        rows = request("GET", "/pods", key)
        rows = rows if isinstance(rows, list) else rows.get("pods", [])
        found = [x for x in rows if x.get("name") == name]
        if len(found) != 1:
            raise RuntimeError("creation response uncertain; no second creation attempted") from None
        pod = found[0]
    created = parse_created(pod) if pod.get("createdAt") else before
    (out / "pod.json").write_text(json.dumps({"id": pod["id"], "name": name, "createdAt": pod.get("createdAt"),
                                              "local_deadline_epoch": local_deadline(created, config)}, indent=2) + "\n")
    print("pod allocated:", pod["id"], flush=True)
    monitor(pod["id"], key, out, pkey, created, config)


if __name__ == "__main__":
    main()
