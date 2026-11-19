"""Start development services and check intended endpoints only; no model/solve."""
import json
from environment import CACHE, HERE, Environment


def main():
    rows = []
    for task in json.loads((HERE/'development_manifest.json').read_text())['tasks']:
        row = {'id': task['id'], 'healthy': False}
        try:
            with Environment(task['id'], discovery=True) as env:
                env.wait_healthy()
            row['healthy'] = True
            print('Development endpoint validated', task['id'], flush=True)
        except Exception as error:
            row['error_type'] = type(error).__name__
            (CACHE/(task['id']+'-development-error.txt')).write_text(str(error))
            print('Development endpoint needs repair', task['id'], flush=True)
        rows.append(row)
    (HERE/'development_health.json').write_text(json.dumps({
        'scope': 'compatibility environment checks only, not model results',
        'tasks': rows, 'model_calls': 0, 'paid_spend_usd': 0}, indent=2)+'\n')
    if not all(row['healthy'] for row in rows):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
