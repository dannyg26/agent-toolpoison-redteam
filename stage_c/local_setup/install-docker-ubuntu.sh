#!/usr/bin/env bash
# Official Docker packages in Ubuntu 24.04. No challenges or model calls are run.
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
    echo "Run this setup as root inside the Ubuntu WSL distribution." >&2
    exit 1
fi
. /etc/os-release
if [ "$ID" != ubuntu ] || [ "$VERSION_ID" != 24.04 ]; then
    echo "This reviewed setup targets Ubuntu 24.04 only." >&2
    exit 1
fi
if [ "$(ps -p 1 -o comm=)" != systemd ]; then
    echo "WSL must boot this distribution with systemd before Docker is installed." >&2
    exit 2
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update -o Acquire::Retries=3
apt-get install -y ca-certificates curl python3 python3-venv
install -m 0755 -d /etc/apt/keyrings
curl --proto '=https' --tlsv1.2 -fsSL --connect-timeout 15 --max-time 120 \
    https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
if [ -f /etc/apt/sources.list.d/docker.sources ]; then
    if ! grep -q '^URIs: https://download.docker.com/linux/ubuntu$' /etc/apt/sources.list.d/docker.sources; then
        echo "An unexpected Docker repository configuration already exists; inspect it first." >&2
        exit 3
    fi
else
    cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
fi
apt-get update -o Acquire::Retries=3
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl start docker
docker version
docker compose version
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges hello-world
docker image inspect hello-world --format '{{json .RepoDigests}}'
echo 'Docker setup and the benign container check completed.'
