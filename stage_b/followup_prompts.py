"""Attacker system-prompt variants for the framing follow-up (FOLLOWUP-PROTOCOL.md).

AUTHORIZED is the completed study's prompt, byte for byte (harness.ATTACKER_SYSTEM, unchanged and frozen).
NEUTRAL removes ONLY the explicit authorisation wording from its first sentence. The role ("AI red-team agent"),
the benchmark name, the statement that everything is simulated, the mechanism, the output format, the user-turn
prompt (ATTACKER_FIRST) and the feedback text are identical in both.

    python stage_b/followup_prompts.py      # prints the exact difference
"""
import difflib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

AUTHORIZATION_PHRASE = "in an authorized security evaluation of AI assistants, run on"
NEUTRAL_PHRASE = "working on"


def variants(harness_module=None):
    if harness_module is None:
        import harness as harness_module
    authorized = harness_module.ATTACKER_SYSTEM
    if authorized.count(AUTHORIZATION_PHRASE) != 1:
        raise SystemExit("authorisation phrase not found exactly once in harness.ATTACKER_SYSTEM")
    neutral = authorized.replace(AUTHORIZATION_PHRASE, NEUTRAL_PHRASE)
    return {"authorized": authorized, "neutral": neutral}


def first_sentence_diff(v):
    a = v["authorized"].split(". ")[0]
    n = v["neutral"].split(". ")[0]
    return a, n


if __name__ == "__main__":
    v = variants()
    a, n = first_sentence_diff(v)
    print("AUTHORIZED first sentence:\n  " + a + "\nNEUTRAL first sentence:\n  " + n)
    print("\nFull-prompt diff (everything else identical):")
    for line in difflib.unified_diff(v["authorized"].splitlines(), v["neutral"].splitlines(), "authorized", "neutral",
                                     lineterm="", n=0):
        print("  " + line)
