"""Build the arm-blinded F2 hand-labelling sheet (R5-05). Runs after collection; no model, no network.

  python3 make_label_sheet.py OUT_DIR RESULTS.jsonl [RESULTS.jsonl ...]

For every observed F2 trial (infrastructure failures and not_started rows are excluded) it reads the trial's
private trace (next to its results.jsonl) and writes:
  OUT_DIR/label_sheet.csv  shuffled rows: label_id, ended_by, assistant_text, label (blank), notes (blank).
                           assistant_text is the full sequence of assistant turns: each turn's `content`
                           plus the NAMES of the tools it called ("[tool call: terminal]"). Tool arguments,
                           tool outputs, the arm, model, task id and repeat are never written; the trial's
                           fresh secret and any flag-like string (csawctf{...}, flag{...}) in the text are
                           replaced by [TOKEN], so the sheet carries no flag and no arm identity.
  OUT_DIR/label_key.json   private mapping label_id -> (arm, task_id, repeat) and the shuffle seed.
OUT_DIR must be outside the repository (the sheet holds model text); it is created with mode 0700.
Labels (definitions in F-PROTOCOL): refused / refused_after_engaging / complied.
"""
import csv
import json
import os
from pathlib import Path
import random
import re
import secrets
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.resolve()


def trace_path(results_path, row):
    return Path(results_path).parent/('%s-r%d-%s-trace.jsonl' % (row['task_id'], row['repeat'], row['arm']))


FLAG_LIKE = re.compile(r'(?:csawctf|flag)\{[^}]*\}', re.IGNORECASE)   # redacted from the sheet


def assistant_text(trace):
    turns, secrets_seen = [], []
    events = [json.loads(l) for l in Path(trace).read_text().splitlines() if l.strip()]
    for event in events:
        if event.get("kind") == "private_checker_reference" and event.get("expected_flag"):
            secrets_seen.append(event["expected_flag"])
    for event in events:
        if event.get('kind') != 'model_response':
            continue
        try:
            choice = event['response']['choices'][0]
        except (KeyError, IndexError, TypeError):
            continue
        message = choice.get('message') or {}
        names = [((call or {}).get('function') or {}).get('name') or 'unknown' for call in message.get('tool_calls') or []]
        text = (message.get("content") or "").strip()
        for secret in secrets_seen:
            text = text.replace(secret, "[TOKEN]")
            inner = secret[secret.find('{')+1:-1] if '{' in secret and secret.endswith('}') else ''
            if len(inner) >= 8:                      # the random part on its own, too
                text = text.replace(inner, "[TOKEN]")
        text = FLAG_LIKE.sub("[TOKEN]", text)
        cut = ' [reply reached the length limit]' if choice.get('finish_reason') == 'length' else ''
        calls = ''.join(' [tool call: %s]' % n for n in names)
        turns.append('--- turn %d ---\n%s%s%s' % (len(turns)+1, text or '(no text)', calls, cut))
    return '\n'.join(turns) if turns else '(no assistant turns)'


def build(out_dir, results_paths, seed=None):
    out_dir = Path(out_dir).resolve()
    folded = os.path.normcase(str(out_dir)).lower()          # case-insensitive (Windows drives via /mnt/c)
    repo = os.path.normcase(str(REPO)).lower()
    if folded == repo or folded.startswith(repo.rstrip('/\\') + os.sep):
        raise ValueError('Write the label sheet outside the repository')
    out_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(out_dir, 0o700)
    trials = []
    for path in results_paths:
        for line in Path(path).read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row['status'] in ('infrastructure_failure', 'not_started'):
                continue
            trials.append((row, assistant_text(trace_path(path, row))))
    seed = secrets.randbits(64) if seed is None else seed
    random.Random(seed).shuffle(trials)
    key = {'seed': seed, 'labels': {}}
    with (out_dir/'label_sheet.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['label_id', 'ended_by', 'assistant_text', 'label', 'notes'])
        for number, (row, text) in enumerate(trials, 1):
            label_id = 'L%03d' % number
            key['labels'][label_id] = {'arm': row['arm'], 'task_id': row['task_id'], 'repeat': row['repeat']}
            ended = 'solved' if row['status'] == 'solved' else str(row.get('reason'))
            writer.writerow([label_id, ended, text, '', ''])
    (out_dir/'label_key.json').write_text(json.dumps(key, indent=1)+'\n')
    for name in ('label_sheet.csv', 'label_key.json'):
        os.chmod(out_dir/name, 0o600)
    return len(trials)


if __name__ == '__main__':
    print('rows written:', build(sys.argv[1], sys.argv[2:]))
