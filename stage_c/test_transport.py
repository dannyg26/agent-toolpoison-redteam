"""Transport tests against a local synthetic HTTP server; no model/API charges."""
import http.server
import json
import threading
import time
import unittest

from endpoint_client import ContextBudgetExceeded, EndpointClient


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.state = {'mode': 'ok', 'requests': 0}
        state = self.state
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *unused):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                state['requests'] += 1
                if state['mode'] == 'context':
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'maximum context length exceeded')
                    return
                self.send_response(200)
                self.end_headers()
                if state['mode'] == 'trickle':
                    try:
                        for unused in range(50):
                            self.wfile.write(b' ')
                            self.wfile.flush()
                            time.sleep(.05)
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                    return
                self.wfile.write(json.dumps({'model': 'csc-test', 'choices': [{'message': {
                    'role': 'assistant', 'content': 'fixture'}}],
                    'usage': {'completion_tokens': 1}}).encode())
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f'http://127.0.0.1:{self.server.server_port}/v1'
        self.config = {'temperature': .6, 'top_p': .95, 'top_k': 20, 'thinking_budget_per_request': 1024}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_live_calls_disabled_by_default(self):
        with self.assertRaises(PermissionError):
            EndpointClient(self.endpoint, 'csc-test', self.config)
        self.assertEqual(self.state['requests'], 0)

    def test_local_round_trip(self):
        client = EndpointClient(self.endpoint, 'csc-test', self.config, approved=True)
        response = client.complete([], [], max_tokens=10, remaining_seconds=3)
        self.assertEqual(response['usage']['completion_tokens'], 1)

    def test_slow_stream_is_killed_at_total_deadline(self):
        self.state['mode'] = 'trickle'
        client = EndpointClient(self.endpoint, 'csc-test', self.config, approved=True)
        start = time.monotonic()
        with self.assertRaises(TimeoutError):
            client.complete([], [], max_tokens=10, remaining_seconds=.25)
        self.assertLess(time.monotonic()-start, 1.5)

    def test_context_budget_is_distinguished_from_transport_failure(self):
        self.state['mode'] = 'context'
        client = EndpointClient(self.endpoint, 'csc-test', self.config, approved=True)
        with self.assertRaises(ContextBudgetExceeded):
            client.complete([], [], max_tokens=10, remaining_seconds=3)

    def test_wrong_served_model_is_rejected(self):
        client = EndpointClient(self.endpoint, 'different-model', self.config, approved=True)
        with self.assertRaises(RuntimeError):
            client.complete([], [], max_tokens=10, remaining_seconds=3)

    def test_credentials_in_url_are_rejected(self):
        with self.assertRaises(ValueError):
            EndpointClient('https://user:password@example.com/v1', 'csc-test', self.config, approved=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
