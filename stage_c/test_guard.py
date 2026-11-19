import json
from pathlib import Path
import unittest

from guard_adapter import guard_config, verify_ready
from inference_server import serving_command
from flag_patch import replace_secret, validate_template

CONFIG = json.loads((Path(__file__).resolve().parent/'study_config.json').read_text())
POD = {'id': 'testpod123', 'createdAt': '2026-11-18T00:00:00Z'}
CREATED = 1794960000.0


class GuardTests(unittest.TestCase):
    def test_three_hour_cap_includes_startup(self):
        from guard_adapter import guard
        created = guard.parse_created(POD)
        ready = {'pod_id': POD['id'], 'deadline_epoch': created+10800}
        self.assertEqual(verify_ready(ready, POD, CONFIG, created+60, 2.22), created+10800)
        wrong = dict(ready, deadline_epoch=created+10900)
        with self.assertRaises(ValueError):
            verify_ready(wrong, POD, CONFIG, created+60, 2.22)

    def test_wrong_pod_and_expired_guard_fail(self):
        from guard_adapter import guard
        created = guard.parse_created(POD)
        with self.assertRaises(ValueError):
            verify_ready({'pod_id': 'other', 'deadline_epoch': created+10800}, POD, CONFIG, created, 2.22)
        with self.assertRaises(ValueError):
            verify_ready({'pod_id': POD['id'], 'deadline_epoch': created+10800}, POD, CONFIG, created+10801, 2.22)

    def test_quote_limits(self):
        from guard_adapter import guard
        created = guard.parse_created(POD)
        ready = {'pod_id': POD['id'], 'deadline_epoch': created+10800}
        for price in [0, float('nan'), 2.23]:
            with self.assertRaises(ValueError):
                verify_ready(ready, POD, CONFIG, created, price)

    def test_model_pins_and_localhost_binding(self):
        for condition in ('main', 'control'):
            args = serving_command(CONFIG, condition)
            self.assertIn(CONFIG[condition+'_revision'], args)
            self.assertEqual(args[args.index('--host')+1], '127.0.0.1')
            self.assertIn('csc-'+condition, args)

    def test_plaintext_replacement_preserves_other_bytes(self):
        old, new = 'flag{'+'a'*20+'}', 'flag{'+'b'*20+'}'
        source = ('prefix\n'+old+'\nsuffix').encode()
        patched = replace_secret(source, old, new)
        self.assertEqual(patched, ('prefix\n'+new+'\nsuffix').encode())
        with self.assertRaises(ValueError):
            replace_secret(source, old, 'flag{short}')
        with self.assertRaises(ValueError):
            validate_template(b'\x00'+source, old)


if __name__ == '__main__':
    unittest.main(verbosity=2)
