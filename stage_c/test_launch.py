"""Offline launcher checks: no network, no pod, no spend."""
import io
import json
import tarfile
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

    def test_background_pod_commands_release_ssh(self):
        # A backgrounded command that inherits SSH stdin keeps the session open (lease 1 failure).
        source = (HERE/'launch_ctf.py').read_text()
        self.assertGreaterEqual(source.count('nohup'), 3)
        for line in source.splitlines():
            if line.rstrip().endswith("&'") or "&' %" in line:
                self.assertIn('< /dev/null &', line)

    def test_quote_includes_disk(self):
        self.assertAlmostEqual(L.quoted_hourly(2.0), 2.0 + 200*0.10/720)


if __name__ == '__main__':
    unittest.main()
