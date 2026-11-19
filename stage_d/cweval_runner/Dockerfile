# Offline runner for CWEval Python tests. Generated code runs here with --network none, a non-root
# user, no capabilities and a read-only root filesystem (see score_run1.run_cweval).
FROM python:3.12.7-slim-bookworm
RUN pip install --no-cache-dir \
      pytest==8.3.3 pytest-timeout==2.3.1 wrapt_timeout_decorator==1.5.1 \
      lxml==5.3.0 PyYAML==6.0.2 PyJWT==2.9.0 argon2-cffi==23.1.0 pycryptodome==3.21.0 \
 && useradd -u 10001 -m runner
USER 10001
WORKDIR /work
