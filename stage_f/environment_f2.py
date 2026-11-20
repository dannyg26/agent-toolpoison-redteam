"""F2 sandbox: the frozen CTF v2 environment plus one extra network alias for the target.

Every service that carries the task's declared host alias (e.g. pwn.chal.csaw.io) also gets the generic
alias framing_f2.TARGET_ALIAS, so the prompt can name the target without revealing the CTF hostname.
Isolation, fresh secrets, the reachability gate and grading are inherited unchanged. The reachability gate
probes the generic alias, which is the name the model is given.
"""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'stage_e'))
sys.path.insert(0, str(HERE.parent/'stage_c'))
from environment_v2 import EnvironmentV2  # noqa: E402
from framing_f2 import TARGET_ALIAS  # noqa: E402


def add_alias(document, box, alias=TARGET_ALIAS):
    """Add `alias` next to `box` in every service network alias list. Returns how many were added."""
    added = 0
    for service in document['services'].values():
        networks = service.get('networks')
        if not isinstance(networks, dict):
            continue
        for settings in networks.values():
            aliases = (settings or {}).get('aliases') or []
            if box in aliases and alias not in aliases:
                aliases.append(alias)
                added += 1
    return added


class EnvironmentF2(EnvironmentV2):
    def __init__(self, task_id, discovery=False, agent_image=None):
        super().__init__(task_id, discovery=discovery, agent_image=agent_image)
        if add_alias(self.document, self.metadata['box']) < 1:
            raise ValueError('Target alias could not be added for '+task_id)
        self.compose_path.write_text(json.dumps(self.document, indent=2))
        self.compose_path.chmod(0o600)
        self.metadata = dict(self.metadata, box=TARGET_ALIAS)   # gate and prompt use the generic name
