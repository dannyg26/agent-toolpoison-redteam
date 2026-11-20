"""Free check (no model): for each F2 task, the generic alias resolves and the target accepts a fresh
connection from the agent container; the F2 prompt names the alias, never the old CTF hostname and contains
none of the cue words in PROMPT_CUE_WORDS. Every field is part of all_ok (R5-02).
Writes /home/capstone-study/stage_f/f2_environment_check.json. No flag is printed."""
import json
from pathlib import Path
import re
import sys

from environment_f2 import EnvironmentF2
from framing_f2 import TARGET_ALIAS, task_prompt_f2

TASKS = json.loads((Path(__file__).resolve().parent/'f_config.json').read_text())['f2']['tasks']
CACHE = Path('/home/capstone-study/stage_f')
PROMPT_CUE_WORDS = ('ctf', 'challenge', 'competition', 'csaw')     # 'flag' is unavoidable via submit_flag
FIELDS = ('alias_resolves', 'prompt_names_alias', 'prompt_free_of_csaw_host', 'prompt_free_of_cue_words')


def prompt_free_of_cue_words(prompt):
    return not re.search('|'.join(PROMPT_CUE_WORDS), prompt, re.IGNORECASE)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    report = {'alias': TARGET_ALIAS, 'prompt_cue_words': list(PROMPT_CUE_WORDS), 'tasks': {}}
    for task_id in (sys.argv[1:] or TASKS):
        with EnvironmentF2(task_id) as env:
            env.wait_healthy()
            attempts = env.wait_reachable()
            dns = env.exec(['getent', 'hosts', TARGET_ALIAS])
            prompt = task_prompt_f2(env.metadata, task_id.split('-')[1])
            row = {'reachable_attempt': attempts, 'alias_resolves': dns['exit_code'] == 0,
                   'prompt_names_alias': TARGET_ALIAS in prompt,
                   'prompt_free_of_csaw_host': 'chal.csaw.io' not in prompt,
                   'prompt_free_of_cue_words': prompt_free_of_cue_words(prompt)}
        report['tasks'][task_id] = row
        print(task_id, row, flush=True)
    report['all_ok'] = all(all(r[f] for f in FIELDS) and r['reachable_attempt'] >= 1
                           for r in report['tasks'].values())
    (CACHE/'f2_environment_check.json').write_text(json.dumps(report, indent=1)+'\n')
    print('ALL OK' if report['all_ok'] else 'PROBLEMS FOUND')


if __name__ == '__main__':
    main()
