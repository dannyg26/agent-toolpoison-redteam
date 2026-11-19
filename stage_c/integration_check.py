"""Local synthetic end-to-end and isolation checks. No model or CTF solve is run."""
import copy
import json
import secrets
import time

from environment import CACHE, HERE, Environment, agent_service, docker, isolated_network
from trajectory import ExactGrader, run_trajectory


def reply(name, arguments):
    return {'choices': [{'message': {'role': 'assistant', 'content': None, 'tool_calls': [
        {'id': 'fixture-tool', 'type': 'function', 'function': {
         'name': name, 'arguments': json.dumps(arguments)}}]}}], 'usage': {'completion_tokens': 10}}


class FixtureClient:
    def complete(self, messages, *unused, **kwargs):
        if messages[-1]['role'] != 'tool':
            return reply('terminal', {'command': "python3 -c \"import urllib.request; print(urllib.request.urlopen('http://challenge:8080').read().decode())\""})
        observed = json.loads(messages[-1]['content'])['output'].strip()
        return reply('submit_flag', {'flag': observed})


def fixture(image, secret):
    agent = agent_service(image)
    target = copy.deepcopy(agent)
    target['networks'] = {'ctfnet': {'aliases': ['challenge']}}
    target['environment'] = dict(target['environment'], FIXTURE_SECRET=secret)
    code = ("import os,http.server; "
            "H=type('H',(http.server.BaseHTTPRequestHandler,),"
            "{'do_GET':lambda self:(self.send_response(200),self.end_headers(),"
            "self.wfile.write(os.environ['FIXTURE_SECRET'].encode())),"
            "'log_message':lambda *args:None}); "
            "http.server.HTTPServer(('0.0.0.0',8080),H).serve_forever()")
    target['command'] = ['python3', '-c', code]
    return {'services': {'agent': agent, 'target': target}, 'networks': {'ctfnet': isolated_network()}}


def main():
    lock = json.loads((CACHE/'image_lock.json').read_text())
    secret = 'flag{'+secrets.token_hex(16)+'}'
    doc = fixture(lock['agent'], secret)
    summary = {'scope': 'synthetic fixture only; scripted responses, no real model calls',
               'model_calls': 0, 'paid_spend_usd': 0}
    with Environment(fixture_document=doc) as env:
        for unused in range(20):
            ready = env.exec(['python3', '-c', "import socket;socket.create_connection(('challenge',8080),timeout=1).close()"])
            if ready['exit_code'] == 0:
                break
            time.sleep(.1)
        else:
            raise RuntimeError('Synthetic fixture server failed')
        info = json.loads(docker('inspect', env.container)['output'])[0]
        assert info['Config']['User'] == '10001:10001'
        assert info['HostConfig']['ReadonlyRootfs']
        assert info['HostConfig']['CapDrop'] == ['ALL']
        assert not info['Mounts'] or all(mount['Type'] == 'tmpfs' for mount in info['Mounts'])
        assert not info['HostConfig']['PortBindings']
        assert not info['HostConfig']['Privileged']
        code = (
            "import json,os,socket; from pathlib import Path; "
            "routes=Path('/proc/net/route').read_text(); "
            "checks={'uid':os.getuid(),'docker_socket':Path('/var/run/docker.sock').exists(),"
            "'windows_mount':Path('/mnt/c').exists(),'default_route':any("
            "len(x.split())>1 and x.split()[1]=='00000000' for x in routes.splitlines()[1:])}; "
            "Path('/work/reset-probe').write_text('fixture'); print(json.dumps(checks))")
        checks = json.loads(env.exec(['python3', '-c', code])['output'])
        assert checks == {'uid': 10001, 'docker_socket': False, 'windows_mount': False, 'default_route': False}
        external = env.exec(['python3', '-c', "import socket; socket.create_connection(('192.0.2.1',80),timeout=.5)"])
        assert external['exit_code'] != 0
        dns = env.exec(['python3', '-c', "import socket; socket.getaddrinfo('example.com',80)"])
        assert dns['exit_code'] != 0
        config = json.loads((HERE/'study_config.json').read_text())
        result = run_trajectory(FixtureClient(), env, ExactGrader(secret), 'Synthetic fixture', config)
        assert result['solved'] is True and result['tool_calls'] == 2
        summary.update(isolation_checks=checks, external_route_blocked=True,
                       external_dns_blocked=True, scripted_end_to_end_passed=True)
    with Environment(fixture_document=fixture(lock['agent'], 'flag{'+secrets.token_hex(16)+'}')) as env:
        reset = env.exec(['python3', '-c', "from pathlib import Path;assert not Path('/work/reset-probe').exists()"])
        assert reset['exit_code'] == 0
    summary['fresh_agent_filesystem_verified'] = True
    (HERE/'integration_checks.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
