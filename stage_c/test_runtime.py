import copy
import json
import os
import sys
import time
import unittest

from analyze_ctf import summarize
from environment import agent_service, assert_no_host_access, command, compose_document, isolated_network, random_flag
from prepare_assets import resolve
from trajectory import ExactGrader, run_trajectory


CONFIG = {'task_seconds': 5, 'max_tool_calls_per_trajectory': 3,
          'max_flag_submissions_per_trajectory': 2,
          'max_generated_tokens_per_trajectory': 100,
          'max_generated_tokens_per_request': 50}


def response(name=None, arguments=None, tokens=10, calls=None):
    message = {'role': 'assistant', 'content': None}
    if name:
        message['tool_calls'] = [{'id': 't1', 'type': 'function',
            'function': {'name': name, 'arguments': json.dumps(arguments)}}]
    if calls is not None:
        message['tool_calls'] = calls
    return {'choices': [{'message': message}], 'usage': {'completion_tokens': tokens}}


class ScriptedClient:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.requests = []

    def complete(self, *args, **kwargs):
        self.requests.append(kwargs)
        return next(self.replies)


class FakeEnvironment:
    def __init__(self):
        self.commands = []

    def terminal(self, text, remaining):
        self.commands.append(text)
        return {'exit_code': 0, 'output': 'fixture output', 'timed_out': False}


class RuntimeTests(unittest.TestCase):
    def test_resolve_year_and_punctuation(self):
        manifest = {'tasks': [{'id': '2018q-pwn-get_it', 'event': '2018q',
                              'category': 'pwn', 'name': 'get_it'}]}
        index = {'pwn-get-it': {'year': '2018', 'event': 'CSAW-Quals', 'category': 'pwn',
                               'challenge': 'get_it?', 'path': 'ctftiny/pwn/get_it?'}}
        self.assertEqual(resolve(manifest, index)[0]['source_path'], 'ctftiny/pwn/get_it?')
        with self.assertRaises(ValueError):
            resolve(manifest, dict(index, duplicate=index['pwn-get-it']))

    def test_upstream_socket_and_ports_are_removed(self):
        original = {'services': {'target': {'image': 'official:test', 'ports': ['80:80'],
            'volumes': ['/var/run/docker.sock:/var/run/docker.sock'],
            'networks': {'ctfnet': {'aliases': ['challenge']}}}}}
        document = compose_document(original, {'official:test': 'official@sha256:abc'}, 'sha256:def')
        self.assertNotIn('ports', document['services']['target'])
        self.assertNotIn('volumes', document['services']['target'])
        self.assertTrue(document['networks']['ctfnet']['internal'])
        self.assertEqual(document['networks']['ctfnet']['driver_opts'][
            'com.docker.network.bridge.gateway_mode_ipv4'], 'isolated')
        bad = copy.deepcopy(original)
        bad['services']['target']['volumes'] = ['/:/host']
        with self.assertRaises(ValueError):
            compose_document(bad, {'official:test': 'pin'}, 'agent')
        bad = copy.deepcopy(original)
        bad['services']['target']['privileged'] = True
        with self.assertRaises(ValueError):
            compose_document(bad, {'official:test': 'pin'}, 'agent')

    def test_host_network_rejected(self):
        document = {'services': {'agent': agent_service('image')}, 'networks': {'ctfnet': isolated_network()}}
        document['services']['agent']['network_mode'] = 'host'
        with self.assertRaises(ValueError):
            assert_no_host_access(document)

    def test_private_exact_grader(self):
        grader = ExactGrader('flag{fixture}')
        self.assertTrue(grader.check(' flag{fixture}\n'))
        self.assertFalse(grader.check('FLAG{fixture}'))
        self.assertFalse(grader.check(None))
        self.assertFalse(grader.check('flag{wrong}'))

    def test_only_independent_flag_check_creates_success(self):
        environment = FakeEnvironment()
        client = ScriptedClient([response('terminal', {'command': 'echo fixture'}),
                                 response('submit_flag', {'flag': 'flag{fixture}'})])
        result = run_trajectory(client, environment, ExactGrader('flag{fixture}'), 'fixture', CONFIG)
        self.assertEqual(result['status'], 'solved')
        self.assertEqual(result['tool_calls'], 2)
        self.assertEqual(environment.commands, ['echo fixture'])
        final_only = ScriptedClient([response()])
        result = run_trajectory(final_only, FakeEnvironment(), ExactGrader('flag{fixture}'), 'fixture', CONFIG)
        self.assertFalse(result['solved'])

    def test_submission_budget(self):
        client = ScriptedClient([response('submit_flag', {'flag': 'wrong'})]*3)
        result = run_trajectory(client, FakeEnvironment(), ExactGrader('flag{fixture}'), 'fixture', CONFIG)
        self.assertEqual(result['reason'], 'submission_budget')
        self.assertEqual(result['flag_submissions'], 2)

    def test_batched_calls_cannot_bypass_budget(self):
        tool = response('terminal', {'command': 'echo fixture'})['choices'][0]['message']['tool_calls'][0]
        client = ScriptedClient([response(calls=[tool]*10)])
        env = FakeEnvironment()
        result = run_trajectory(client, env, ExactGrader('fixture'), 'fixture', CONFIG)
        self.assertEqual(result['reason'], 'tool_budget')
        self.assertEqual(len(env.commands), 3)

    def test_late_success_is_not_accepted(self):
        now = [0.0]
        class LateClient:
            def complete(self, *unused, **kwargs):
                now[0] = 6
                return response('submit_flag', {'flag': 'flag{fixture}'})
        result = run_trajectory(LateClient(), FakeEnvironment(), ExactGrader('flag{fixture}'),
                                'fixture', CONFIG, clock=lambda: now[0])
        self.assertEqual(result['reason'], 'time_budget')
        self.assertFalse(result['solved'])

    def test_bad_token_accounting_is_infrastructure_error(self):
        for tokens in [None, True, -1, 1000]:
            client = ScriptedClient([response(tokens=tokens)])
            result = run_trajectory(client, FakeEnvironment(), ExactGrader('fixture'), 'fixture', CONFIG)
            self.assertEqual(result['status'], 'infrastructure_failure')
            self.assertIsNone(result['solved'])

    def test_unknown_tool_never_executes(self):
        client = ScriptedClient([response('host_shell', {'command': 'echo fixture'}), response()])
        env = FakeEnvironment()
        result = run_trajectory(client, env, ExactGrader('fixture'), 'fixture', CONFIG)
        self.assertEqual(env.commands, [])
        self.assertFalse(result['solved'])

    def test_missing_results_and_duplicate_runs(self):
        tasks = [{'id': 'one'}, {'id': 'two'}]
        row = {'task_id': 'one', 'condition': 'main', 'status': 'solved', 'solved': True}
        result = summarize(tasks, [row])
        self.assertEqual(result['arms']['main']['bounds_over_planned'], [.5, 1])
        self.assertEqual(result['paired_descriptive_only']['complete_pairs'], 0)
        with self.assertRaises(ValueError):
            summarize(tasks, [row, row])

    def test_fresh_flag_format(self):
        original = 'flag{'+'a'*32+'}'
        fresh = random_flag(original)
        self.assertEqual(len(fresh), len(original))
        self.assertTrue(fresh.startswith('flag{'))
        self.assertNotEqual(fresh, original)
        with self.assertRaises(ValueError):
            random_flag('flag{short}')

    @unittest.skipUnless(os.name == 'posix', 'Real process deadlines tested inside Linux')
    def test_trickled_output_cannot_extend_deadline(self):
        code = 'import time,sys\nwhile True:\n print("x",flush=True);time.sleep(.01)'
        start = time.monotonic()
        result = command([sys.executable, '-c', code], timeout=.25, check=False)
        self.assertTrue(result['timed_out'])
        self.assertLess(time.monotonic()-start, 2)

    @unittest.skipUnless(os.name == 'posix', 'Linux process test')
    def test_output_retention_is_bounded(self):
        result = command([sys.executable, '-c', 'print("x"*100000)'], limit=100)
        self.assertTrue(result['truncated'])
        self.assertEqual(len(result['output']), 100)


if __name__ == '__main__':
    unittest.main(verbosity=2)
