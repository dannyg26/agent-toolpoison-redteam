"""A cleanup failure must not erase a verified result or start another trial."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import run_phase


class PhaseTests(unittest.TestCase):
    def test_cleanup_failure_preserves_result_and_stops_phase(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = json.loads((Path(__file__).resolve().parent/'study_config.json').read_text())
            source['allow_live_model_calls'] = True
            (root/'study_config.json').write_text(json.dumps(source))
            tasks = [{'id': str(index)} for index in range(14)]
            (root/'challenge_manifest.json').write_text(json.dumps({'tasks': tasks}))
            starts = []
            class FakeEnvironment:
                def __init__(self, task):
                    starts.append(task)
                    self.expected_flag = 'fixture'
                    self.metadata = {'description': 'fixture', 'box': 'fixture', 'internal_port': 1}
                def __enter__(self):
                    return self
                def wait_healthy(self):
                    pass
                def __exit__(self, *unused):
                    raise RuntimeError('simulated cleanup failure')
            class FakeClient:
                def __init__(self, *unused, **kwargs):
                    pass
                def complete(self, *unused, **kwargs):
                    return {'choices': [{'message': {'role': 'assistant', 'tool_calls': [{
                        'id': 'fixture', 'function': {'name': 'submit_flag',
                        'arguments': '{"flag":"fixture"}'}}]}}], 'usage': {'completion_tokens': 1}}
            argv = ['run_phase.py', '--phase', 'main-1', '--endpoint', 'http://127.0.0.1',
                    '--session', 'fixture', '--soft-stop-epoch', str(time.time()+3600), '--run-approved']
            with patch.object(run_phase, 'HERE', root), patch.object(run_phase, 'CACHE', root/'cache'), \
                 patch.object(run_phase, 'Environment', FakeEnvironment), \
                 patch.object(run_phase, 'EndpointClient', FakeClient), \
                 patch.object(run_phase, 'require_freeze'), patch.object(sys, 'argv', argv), \
                 patch('builtins.print'):
                with self.assertRaises(RuntimeError):
                    run_phase.main()
            rows = [json.loads(line) for line in (root/'cache/private/fixture/results.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertTrue(rows[0]['solved'])
            self.assertTrue(rows[0]['environment_cleanup_error'])
            self.assertEqual(len(starts), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
