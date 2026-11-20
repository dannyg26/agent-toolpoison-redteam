"""Free check (no model): for each F2 task, the generic alias resolves and the target accepts a fresh
connection from the agent container; the old CTF hostname is not used in the F2 prompt.
Writes /home/capstone-study/stage_f/f2_environment_check.json. No flag is printed."""
import json
from pathlib import Path
import sys

from environment_f2 import EnvironmentF2
from framing_f2 import TARGET_ALIAS, task_prompt_f2

TASKS = json.loads((Path(__file__).resolve().parent/'f_config.json').read_text())['f2']['tasks']
CACHE = Path('/home/capstone-study/stage_f')


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    report = {'alias': TARGET_ALIAS, 'tasks': {}}
    for task_id in (sys.argv[1:] or TASKS):
        with EnvironmentF2(task_id) as env:
            env.wait_healthy()
            attempts = env.wait_reachable()
            dns = env.exec(['getent', 'hosts', TARGET_ALIAS])
            prompt = task_prompt_f2(env.metadata, task_id.split('-')[1])
            row = {'reachable_attempt': attempts, 'alias_resolves': dns['exit_code'] == 0,
                   'prompt_names_alias': TARGET_ALIAS in prompt,
                   'prompt_free_of_csaw_host': 'chal.csaw.io' not in prompt}
        report['tasks'][task_id] = row
        print(task_id, row, flush=True)
    report['all_ok'] = all(r['alias_resolves'] and r['prompt_names_alias'] and r['reachable_attempt'] >= 1
                           for r in report['tasks'].values())
    (CACHE/'f2_environment_check.json').write_text(json.dumps(report, indent=1)+'\n')
    print('ALL OK' if report['all_ok'] else 'PROBLEMS FOUND')


if __name__ == '__main__':
    main()
