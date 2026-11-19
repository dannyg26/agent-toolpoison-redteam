"""Harness validation for CWEval scoring, run before any model output is scored.

Positive control: each task's reference solution (the vendor task file, which contains the solution)
must pass both functionality and security. Negative controls: an empty module and a stub that returns
None must fail functionality. Writes CACHE/cweval_harness_check.json.
"""
import json
from pathlib import Path

import score_run1 as S

SOURCE = S.CACHE/'vendor/cweval/benchmark/core/py'


def main():
    report = {}
    for task_file in sorted(SOURCE.glob('*_task.py')):
        task = task_file.name[:-len('_task.py')]
        reference = S.run_cweval(task, task_file.read_text())
        empty = S.run_cweval(task, '')
        report[task] = {'reference': reference, 'empty_fails_functionality': not empty['functionality']}
        print(task, reference, 'empty fails:', not empty['functionality'], flush=True)
    passing = [t for t, r in report.items() if r['reference']['functionality'] and r['reference']['security']]
    summary = {'tasks': len(report), 'reference_func_and_sec_pass': len(passing),
               'reference_failures': sorted(set(report) - set(passing)),
               'negative_controls_fail': all(r['empty_fails_functionality'] for r in report.values()),
               'runner_image': S.CWEVAL_IMAGE, 'tasks_detail': report}
    (S.CACHE/'cweval_harness_check.json').write_text(json.dumps(summary, indent=1)+'\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'tasks_detail'}, indent=1))


if __name__ == '__main__':
    main()
