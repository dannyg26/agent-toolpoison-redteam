FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash coreutils ca-certificates curl wget netcat-openbsd socat file binutils \
    gdb gcc g++ make unzip zip libc6-i386 python3 python3-venv git procps \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/ctf-tools \
    && /opt/ctf-tools/bin/pip install --no-cache-dir pwntools==4.15.1 requests==2.34.2 \
    && /opt/ctf-tools/bin/pip freeze > /opt/ctf-package-versions.txt
ENV PATH=/opt/ctf-tools/bin:$PATH HOME=/work TERM=xterm
RUN groupadd -g 10001 ctfagent && useradd -u 10001 -g 10001 -d /work ctfagent
USER 10001:10001
WORKDIR /work
CMD ["sleep", "infinity"]
