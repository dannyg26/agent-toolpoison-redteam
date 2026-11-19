"""Free local check of the v2 harness fixes on real sandboxes (no model). Writes CACHE/v2_environment_check.json.

Covers the 14 test tasks and the 3 development tasks (development tasks use discovery mode, as in
run_arm_v2.py). For each task: the agent uses the v2 image; every ELF starter file is executable; the
stated host:port passes the same reachability gate the trials use (EnvironmentV2.wait_reachable: fresh
`nc -z -w 3` from inside the agent container, up to 10 attempts 3 s apart, after the base wait_healthy);
the prompt states host and port. `all_ok` requires all of these for every task. No flag is printed.
"""
import json
from pathlib import Path
import sys

from environment_v2 import EnvironmentV2, TargetUnreachable, agent_v2_image_id, task_prompt

HERE = Path(__file__).resolve().parent
CACHE = Path('/home/capstone-study/stage_e')


def manifest(name):
    return [t['id'] for t in json.loads((HERE.parent/'stage_c'/name).read_text())['tasks']]


TEST_TASKS, DEVELOPMENT_TASKS = manifest('challenge_manifest.json'), manifest('development_manifest.json')


def is_elf(path):
    with open(path, 'rb') as stream:
        return stream.read(4) == b'\x7fELF'


def check_task(task_id, image):
    row = {'phase': 'development' if task_id in DEVELOPMENT_TASKS else 'test'}
    with EnvironmentV2(task_id, discovery=(row['phase'] == 'development')) as env:
        env.wait_healthy()
        try:
            row['reachability_attempts'] = env.wait_reachable()
            row['target_reachable'] = True
        except TargetUnreachable as error:
            row['reachability_attempts'], row['target_reachable'] = error.attempts, False
        meta = env.metadata
        box, port = meta['box'], meta['internal_port']
        row['agent_image_is_v2'] = base_docker('inspect', env.container, '--format', '{{.Image}}') == image
        executable = []
        for filename in meta.get('files', []):
            result = env.exec(['bash', '-c', 'test -x "/work/$1" && echo X || echo -', '_', filename])
            elf = is_elf((env.task_directory/filename).resolve())
            executable.append({'file': filename, 'elf': elf, 'mode': result['output'].strip()})
        row['starter_exec'] = executable
        row['elf_starters_executable'] = all(e['mode'] == 'X' for e in executable if e['elf'])
        prompt = task_prompt(meta, task_id.split('-')[1])
        row['prompt_has_target'] = box in prompt and str(port) in prompt
    row['ok'] = all(row[k] for k in ('agent_image_is_v2', 'target_reachable', 'elf_starters_executable',
                                     'prompt_has_target'))
    return row


def main():
    tasks = sys.argv[1:] or TEST_TASKS + DEVELOPMENT_TASKS
    CACHE.mkdir(parents=True, exist_ok=True)
    image = agent_v2_image_id()
    report = {'agent_v2_image': image, 'tasks': {}}
    for task_id in tasks:
        row = check_task(task_id, image)
        report['tasks'][task_id] = row
        print(task_id, row, flush=True)
    report['all_ok'] = all(r['ok'] for r in report['tasks'].values())
    report['complete'] = sorted(report['tasks']) == sorted(TEST_TASKS + DEVELOPMENT_TASKS)
    if not sys.argv[1:]:
        (CACHE/'v2_environment_check.json').write_text(json.dumps(report, indent=1)+'\n')
    print('ALL OK' if report['all_ok'] and report['complete'] else
          'PROBLEMS FOUND' if not report['all_ok'] else 'PARTIAL RUN (not written)')


def base_docker(*args):
    import environment
    return environment.docker(*args, timeout=30)['output'].strip()


if __name__ == '__main__':
    main()
