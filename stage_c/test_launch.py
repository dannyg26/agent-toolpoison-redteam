"""Offline launcher checks: no network, no pod, no spend."""
import io
import json
import subprocess
import tarfile
import time
import unittest
from unittest import mock

import launch_ctf as L
from environment import HERE

CONFIG = json.loads((HERE/'study_config.json').read_text())


def fake_api(pods=(), price=1.89):
    def api(method, path, key, body=None, timeout=30):
        assert method == 'GET', 'preflight must be read-only'
        if path == '/pods':
            return list(pods)
        if path == '/catalog/gpus':
            return {'gpus': [{'id': L.GPU, 'price': {'secure': price}}]}
        raise AssertionError(path)
    return api


class LaunchTests(unittest.TestCase):
    def preflight(self, pods=(), price=1.89, balance=11.0, spend=0.0):
        with mock.patch.object(L, 'api', fake_api(pods, price)), \
                mock.patch.object(L, 'read_balance', return_value=(balance, spend)):
            return L.preflight('k', 'b', CONFIG)

    def test_preflight_accepts_quote_within_cap(self):
        result = self.preflight()
        self.assertTrue(result['ok'])
        self.assertLessEqual(result['quoted_hourly_with_disk'], 2.22)

    def test_preflight_rejects_each_unsafe_condition(self):
        self.assertFalse(self.preflight(pods=[{'id': 'x'}])['ok'])
        self.assertFalse(self.preflight(price=2.30)['ok'])
        self.assertFalse(self.preflight(balance=5.0)['ok'])
        self.assertFalse(self.preflight(spend=0.5)['ok'])

    def test_steps_follow_protocol_order_and_check_each_model_first(self):
        phases = [value for kind, value in L.STEPS if kind == 'phase']
        self.assertEqual(phases, ['main-1', 'control-1', 'control-2', 'main-2'])
        seen = set()
        for kind, value in L.STEPS:
            if kind == 'smoke':
                seen.add(value)
            if kind == 'phase':
                self.assertIn(value.split('-')[0], seen, 'development check must precede first block')

    def test_package_has_pod_side_files_and_no_secrets_or_cache(self):
        with mock.patch.object(L, 'HERE', HERE):
            missing = not (HERE/'ctf_freeze.json').exists()
            if missing:
                (HERE/'ctf_freeze.json').write_text('{}')
            try:
                data = L.package_source()
            finally:
                if missing:
                    (HERE/'ctf_freeze.json').unlink()
        names = tarfile.open(fileobj=io.BytesIO(data)).getnames()
        for needed in ('stage_c/inference_server.py', 'stage_c/guard_adapter.py', 'stage_c/budget.py',
                       'stage_c/study_config.json', 'stage_c/ctf_freeze.json', 'stage_b/pod_guard.py'):
            self.assertIn(needed, names)
        for forbidden in ('flag_patch.py', 'trajectory.py', 'run_phase.py', 'environment_private',
                          'challenge_manifest.json'):
            self.assertNotIn('stage_c/'+forbidden, names)
        self.assertFalse([n for n in names if 'private' in n or 'key' in n.lower()])

    def test_background_helper_returns_immediately_under_pipes(self):
        # bash -c with piped stdout behaves like an SSH session channel; leases 1 and 2 hung here.
        for workdir in (None, '/tmp'):
            command = L.background('sleep 8', '/tmp/ctf-bg-test.log', workdir)
            started = time.monotonic()
            subprocess.run(['bash', '-c', command], input=b'', capture_output=True, timeout=4, check=True)
            self.assertLess(time.monotonic()-started, 2)

    def test_old_background_form_is_known_to_hang(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run(['bash', '-c', 'cd /tmp && nohup sleep 8 > /tmp/ctf-bg-test.log 2>&1 < /dev/null &'],
                           input=b'', capture_output=True, timeout=2)

    def test_stop_vllm_does_not_kill_its_own_shell(self):
        result = subprocess.run(['bash', '-c', L.STOP_VLLM], capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0)

    def test_every_detached_pod_command_uses_the_helper(self):
        commands = []
        class FakePod:
            def run(self, command, stdin=None, timeout=120, check=True):
                commands.append(command)
                out = json.dumps({'pod_id': 'pod12345', 'deadline_epoch': 1}).encode()
                return subprocess.CompletedProcess(command, 0, stdout=out if command.startswith('cat ') else
                                                   ('csc-main' if 'curl' in command else '').encode(), stderr=b'')
        with mock.patch.object(L, 'wait_until', return_value=True),                 mock.patch.object(L, 'package_source', return_value=b'x'):
            L.setup_pod(FakePod(), 'k', 'pod12345', 2.2, CONFIG)
            L.serve(FakePod(), 'main', 'pod12345', 2.2, 1)
        detached = [c for c in commands if 'nohup' in c]
        self.assertEqual(len(detached), 3)
        for command in detached:
            self.assertTrue(command.startswith('(') and command.endswith('&)'), command)
        self.assertFalse([c for c in commands if 'pkill' in c and '[v]llm' not in c])

    def test_quote_includes_disk(self):
        self.assertAlmostEqual(L.quoted_hourly(2.0), 2.0 + 200*0.10/720)


if __name__ == '__main__':
    unittest.main()
