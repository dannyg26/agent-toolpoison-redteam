"""Free local check of the v2 harness fixes on real sandboxes (no model). Writes CACHE/v2_environment_check.json.

For each task: agent uses the v2 image; ELF starter files are executable; the stated host:port accepts a
TCP connection from inside the agent container; the prompt states host and port. No flag is printed.
"""
import json
from pathlib import Path
import sys

from environment_v2 import EnvironmentV2, agent_v2_image_id, task_prompt

TASKS = sys.argv[1:] or [t['id'] for t in json.loads(
    (Path(__file__).resolve().parent.parent/'stage_c/challenge_manifest.json').read_text())['tasks']]
CACHE = Path('/home/capstone-study/stage_e')


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    image = agent_v2_image_id()
    report = {'agent_v2_image': image, 'tasks': {}}
    for task_id in TASKS:
        row = {}
        with EnvironmentV2(task_id) as env:
            env.wait_healthy()
            meta = env.metadata
            box, port = meta['box'], meta['internal_port']
            inspect = base_docker('inspect', env.container, '--format', '{{.Image}}')
            row['agent_image_is_v2'] = inspect == image
            executable = []
            for filename in meta.get('files', []):
                result = env.exec(['bash', '-c', 'test -x /work/%s && echo X || echo -' % filename])
                executable.append((filename, result['output'].strip()))
            row['starter_exec'] = executable
            probe = env.exec(['bash', '-c', 'nc -z -w 5 %s %s && echo OPEN || echo CLOSED' % (box, port)], timeout=15)
            row['target_reachable'] = probe['output'].strip().endswith('OPEN')
            prompt = task_prompt(meta, task_id.split('-')[1])
            row['prompt_has_target'] = box in prompt and str(port) in prompt
        report['tasks'][task_id] = row
        print(task_id, row, flush=True)
    report['all_ok'] = all(r['agent_image_is_v2'] and r['target_reachable'] and r['prompt_has_target']
                           for r in report['tasks'].values())
    (CACHE/'v2_environment_check.json').write_text(json.dumps(report, indent=1)+'\n')
    print('ALL OK' if report['all_ok'] else 'PROBLEMS FOUND')


def base_docker(*args):
    import environment
    return environment.docker(*args, timeout=30)['output'].strip()


if __name__ == '__main__':
    main()
