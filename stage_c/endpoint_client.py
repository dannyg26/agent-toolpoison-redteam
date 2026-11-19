"""OpenAI-compatible model transport with a total process deadline. No provisioning."""
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


class ContextBudgetExceeded(Exception):
    pass


class EndpointClient:
    def __init__(self, endpoint, model, config, approved=False):
        if not approved:
            raise PermissionError('Live model calls are disabled without explicit approval')
        url = urllib.parse.urlsplit(endpoint)
        if url.username or url.password or url.query or url.fragment:
            raise ValueError('Endpoint credentials must be supplied via environment, not URLs')
        if url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ('127.0.0.1', 'localhost')):
            raise ValueError('Model endpoint requires HTTPS or a loopback test server')
        if url.scheme == 'https' and not (url.hostname or '').endswith('.proxy.runpod.net'):
            raise ValueError('Use this project\'s RunPod proxy or a loopback SSH tunnel, not a paid model API')
        self.endpoint, self.model, self.config = endpoint.rstrip('/'), model, config

    def complete(self, messages, tools, max_tokens, remaining_seconds):
        request = {'endpoint': self.endpoint, 'payload': {
            'model': self.model, 'messages': messages, 'tools': tools, 'tool_choice': 'auto',
            'temperature': self.config['temperature'], 'top_p': self.config['top_p'],
            'top_k': self.config['top_k'], 'max_tokens': max_tokens,
            'seed': self.config.get('seed', 20261118),
            'chat_template_kwargs': {'enable_thinking': True,
                                    'thinking_budget': self.config['thinking_budget_per_request']}}}
        # Killing this worker bounds the full response duration, including a slow/trickled body.
        try:
            worker = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker'],
                input=json.dumps(request), text=True, capture_output=True,
                timeout=max(.01, remaining_seconds))
        except subprocess.TimeoutExpired as error:
            raise TimeoutError('Model request reached its total deadline') from error
        if worker.returncode:
            raise RuntimeError('Model transport worker failed')
        response = json.loads(worker.stdout)
        if response.get('_transport_error') == 'context_budget':
            raise ContextBudgetExceeded('Server reported the configured context limit')
        if response.get('_transport_error'):
            raise RuntimeError(response['_transport_error'])
        if response.get('model') != self.model:
            raise RuntimeError('Response model name differs from the requested served model')
        return response


def worker():
    spec = json.load(sys.stdin)
    headers = {'Content-Type': 'application/json'}
    key = os.environ.get('CTF_MODEL_API_KEY')
    if key:
        headers['Authorization'] = 'Bearer '+key
    request = urllib.request.Request(spec['endpoint']+'/chat/completions',
        data=json.dumps(spec['payload']).encode(), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            raw = response.read(4_000_001)
        if len(raw) > 4_000_000:
            raise ValueError('Model response exceeds the retained response bound')
        result = json.loads(raw)
    except urllib.error.HTTPError as error:
        message = error.read(10000).decode(errors='replace').lower()
        context_limit = error.code == 400 and any(text in message for text in
            ('maximum context length', 'context length exceeded', 'exceeds the context window'))
        result = {'_transport_error': 'context_budget' if context_limit else f'HTTP {error.code}'}
    except Exception as error:
        result = {'_transport_error': type(error).__name__}
    print(json.dumps(result))


if __name__ == '__main__' and sys.argv[1:] == ['--worker']:
    worker()
