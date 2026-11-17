"""Container entrypoint: arm the spending guard BEFORE installing dependencies or serving models."""
import base64
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time


def main():
    os.umask(0o077)
    out, repo = Path("/root/out/stage_b_pilot"), Path("/root/repo")
    out.mkdir(parents=True, exist_ok=True)
    repo.mkdir(parents=True, exist_ok=True)
    payload = base64.b64decode(os.environ.pop("PILOT_SOURCE_B64"))
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        tar.extractall(repo, filter="data")
    private = Path("/root/.pilot_private")
    private.mkdir(mode=0o700, exist_ok=True)
    key_file = private / "pods.key"
    key_file.write_text(os.environ.pop("RUNPOD_GUARD_KEY"), encoding="utf-8")
    key_file.chmod(0o600)
    with (out / "guard.log").open("ab", buffering=0) as log:
        guard = subprocess.Popen([sys.executable, str(repo / "stage_b/pod_guard.py"), "--arm", "--key-file",
                                  str(key_file), "--out", str(out)], stdout=log, stderr=log, start_new_session=True)
    for _ in range(60):
        if guard.poll() is not None:
            raise RuntimeError("pod guard could not arm; local watcher must terminate")
        if (out / "guard_ready.json").exists():
            break
        time.sleep(1)
    else:
        raise RuntimeError("pod guard did not become ready; no benchmark setup started")
    print("GUARD_ARMED", flush=True)
    # One ephemeral SSH key for this pod, used solely for continuous output downloads.
    ssh_dir = Path("/root/.ssh")
    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    (ssh_dir / "authorized_keys").write_text(os.environ.pop("PUBLIC_KEY") + "\n", encoding="utf-8")
    (ssh_dir / "authorized_keys").chmod(0o600)
    Path("/run/sshd").mkdir(exist_ok=True)
    subprocess.run(["ssh-keygen", "-A"], check=True, stdout=subprocess.DEVNULL)
    ssh = subprocess.Popen(["/usr/sbin/sshd", "-D", "-o", "PasswordAuthentication=no", "-o",
                            "PermitRootLogin=prohibit-password"], start_new_session=True)
    os.environ["PILOT_GUARD_PID"] = str(guard.pid)
    os.environ["REPO"], os.environ["OUT"] = str(repo), str(out)
    code = subprocess.call(["bash", str(repo / "stage_b/run_pilot.sh"), "--run"])
    print(f"RUNNER_EXIT={code}; waiting for result download or pod deadline", flush=True)
    # Remain reachable for the local watcher. The independent guard survives runner failure.
    while guard.poll() is None:
        time.sleep(5)
    ssh.terminate()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
