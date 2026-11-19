"""Build the CTF v2 agent image and bind it to its Dockerfile (R2-06). Local Docker only; no model, no spend.

The image is built from stage_e/agent_image/Dockerfile with the label
org.capstone.v2.dockerfile_sha256=<SHA-256 of the Dockerfile, LF-normalised>, tagged
capstone-ctf-agent-v2:prepared, and a build record (image ID, Dockerfile hash, time) is written to
/home/capstone-study/stage_e/agent_v2_build.json. freeze_v2.py requires the label to equal the hash of the
frozen Dockerfile, so a frozen image ID cannot silently come from a different Dockerfile.
Usage (WSL, root): python3 build_agent_v2.py
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from environment_v2 import AGENT_V2_TAG, DOCKERFILE_LABEL, agent_v2_dockerfile_label, agent_v2_image_id

HERE = Path(__file__).resolve().parent
CACHE = Path('/home/capstone-study/stage_e')


def dockerfile_sha256():
    return hashlib.sha256((HERE/'agent_image/Dockerfile').read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def main():
    digest = dockerfile_sha256()
    subprocess.run(['docker', 'build', '--pull=false', '--label', '%s=%s' % (DOCKERFILE_LABEL, digest),
                    '-t', AGENT_V2_TAG, str(HERE/'agent_image')], check=True)
    if agent_v2_dockerfile_label() != digest:
        raise SystemExit('Built image does not carry the Dockerfile hash label')
    record = {'image_tag': AGENT_V2_TAG, 'image_id': agent_v2_image_id(), 'dockerfile_sha256': digest,
              'label': DOCKERFILE_LABEL, 'built_at': datetime.now(timezone.utc).isoformat()}
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE/'agent_v2_build.json').write_text(json.dumps(record, indent=1)+'\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
