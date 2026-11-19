"""Offline launcher and pod-generator tests for stage D run 1. No network, pod, GPU or spend."""
import io
import json
import subprocess
import tarfile
import unittest
from unittest import mock

import launch_run1 as L
import pod_generate as G


class FakeCompletion:
    def __init__(self, text):
        self.text, self.token_ids, self.finish_reason = text, [0]*7, 'stop'


class FakeOutput:
    def __init__(self, text):
        self.outputs = [FakeCompletion(text)]


class FakeLLM:
    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def chat(self, messages, params, use_tqdm=False, chat_template_kwargs=None):
        self.calls.append((len(messages), chat_template_kwargs))
        return [FakeOutput(self.reply(m)) for m in messages]


class FakeParams:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class Launcher(unittest.TestCase):
    def test_budget_and_guard_match_config(self):
        hourly, cap = L.budget()
        self.assertEqual((hourly, cap), (2.22, 6.76))
        self.assertEqual(L.guard_config()['maximum_session_minutes'], 180)

    def test_package_contents(self):
        names = tarfile.open(fileobj=io.BytesIO(L.package())).getnames()
        for needed in ['stage_d/pod_generate.py', 'stage_d/pod_judge.py', 'stage_d/run1_pod.sh',
                       'stage_d/sr_judge.py', 'stage_d/judge_templates.json', 'stage_d/items/injecagent.jsonl',
                       'stage_d/injec/simulated.json', 'stage_d/guard_config.json', 'stage_b/pod_guard.py']:
            self.assertIn(needed, names)
        self.assertFalse([n for n in names if 'key' in n.lower() or 'score_run1' in n or 'vendor' in n])

    def test_preflight_rules(self):
        def api(method, path, key, body=None, timeout=30):
            self.assertEqual(method, 'GET')
            return [] if path == '/pods' else {'gpus': [{'id': L.C.GPU, 'price': {'secure': 2.19}}]}
        with mock.patch.object(L.C, 'api', api), mock.patch.object(L.C, 'read_balance', return_value=(9.0, 0.0)):
            self.assertTrue(L.preflight('k', 'b')['ok'])
        with mock.patch.object(L.C, 'api', api), mock.patch.object(L.C, 'read_balance', return_value=(5.0, 0.0)):
            self.assertFalse(L.preflight('k', 'b')['ok'])

    def test_setup_detaches_with_helper_and_arms_guard_first(self):
        commands = []
        class FakePod:
            def run(self, command, stdin=None, timeout=120, check=True):
                commands.append(command)
                out = json.dumps({'pod_id': 'pod12345', 'deadline_epoch': 1}).encode() if command.startswith('cat ') else b''
                return subprocess.CompletedProcess(command, 0, stdout=out, stderr=b'')
        with mock.patch.object(L.C, 'wait_until', return_value=True):
            L.setup(FakePod(), 'k', 'pod12345')
        detached = [c for c in commands if 'nohup' in c]
        self.assertEqual(len(detached), 2)
        self.assertIn('pod_guard.py --arm', detached[0])
        self.assertIn('run1_pod.sh', detached[1])
        self.assertTrue(all(c.startswith('(') and c.endswith('&)') for c in detached))

    def test_pod_driver_shell_syntax(self):
        self.assertEqual(subprocess.run(['bash', '-n', str(L.HERE/'run1_pod.sh')]).returncode, 0)


class Generator(unittest.TestCase):
    def test_run_batch_records_split_and_settings(self):
        config = json.loads((L.HERE/'run1_config.json').read_text())
        rows = [{'id': 'x', 'step': 1, 'messages': [{'role': 'user', 'content': 'q'}], 'seed': 7, 'max_tokens': 64}]
        llm = FakeLLM(lambda m: 'think</think><answer>B</answer>')
        results, _ = G.run_batch(llm, rows, config, FakeParams)
        self.assertEqual(results[0]['content'], '<answer>B</answer>')
        self.assertTrue(results[0]['thinking_closed'])
        self.assertEqual(llm.calls[0][1], {'enable_thinking': True})

    def test_step_two_only_for_successful_data_stealing_with_cached_response(self):
        config = json.loads((L.HERE/'run1_config.json').read_text())
        items = [json.loads(l) for l in (L.CACHE/'items/injecagent.jsonl').read_text().splitlines()]
        ds = [i for i in items if i['key']['attack'] == 'ds'][:30]
        dh = [i for i in items if i['key']['attack'] == 'dh'][:5]
        injec = L.injec_files()
        prompts = json.loads(injec['prompts.json'])
        tools, simulated = json.loads(injec['tools.json']), json.loads(injec['simulated.json'])
        def reply(entry):
            tool = entry['key']['case']['Attacker Tools'][0]
            return 'Thought: follow it\nAction: %s\nAction Input: %s' % (tool, entry['key']['case']['Tool Parameters'])
        step_one = [{'id': e['id'], 'content': reply(e)} for e in ds+dh]
        rows, unobserved = G.injecagent_step_two_rows(ds+dh, step_one, (prompts['system'], prompts['user']),
                                                      tools, simulated, config)
        self.assertEqual(len(rows)+len(unobserved), len(ds))
        self.assertTrue(all(r['step'] == 2 for r in rows))
        self.assertTrue(all('Observation' in r['messages'][1]['content'] for r in rows))


if __name__ == '__main__':
    unittest.main()
