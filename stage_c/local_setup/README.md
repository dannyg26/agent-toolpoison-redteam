# Free laptop Linux/Docker setup

Authorised by the user on 2026-11-18. No GPU rental or model evaluation is part of this setup.

**Completed 2026-11-18:** WSL 3.0.5, Ubuntu 24.04, Docker Engine 29.10.0 and Compose 5.8.0 are installed.
Both the Docker and Compose benign container checks passed; their containers were removed. Evidence is
saved under ignored `runtime/`. The scripts below are the setup record, not instructions to reinstall.

1. `install-wsl.ps1` runs Microsoft's installer for WSL and Ubuntu 24.04. It requires Windows
   administrator approval, records progress under ignored `runtime/`, and never requests a restart.
2. If Windows reports a restart is required, save work and restart when convenient. Do not rerun the
   installer while the original process is active. The assistant can inspect the saved installer result
   and continue after the user returns.
3. After restarting, check `wsl --list --verbose`. The initial Windows-feature phase can finish before
   Ubuntu is installed. If Ubuntu 24.04 is absent, complete the same reviewed Microsoft installer command:
   `wsl --install --distribution Ubuntu-24.04 --web-download --no-launch`.
4. Once Ubuntu starts, `resume-docker-setup.ps1` runs `install-docker-ubuntu.sh` as Linux root inside
   Ubuntu. It uses Docker's signed official Ubuntu package repository, starts the Docker service and
   verifies Docker/Compose with the benign `hello-world` image. It does not run challenge programs.

Docker Engine is installed inside WSL; a Windows `docker.exe` is not required. The Docker socket is not
exposed over a network, and no Windows firewall ports are opened by these scripts. This is an engine
installation check, not verification of the later CTF isolation design.

References: [Microsoft WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install),
[WSL service support](https://learn.microsoft.com/en-us/windows/wsl/systemd),
[Docker's Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/).
