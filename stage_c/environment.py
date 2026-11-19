"""Linux-only CTF environment control. The model never receives Docker access."""
import copy
import hashlib
import json
import os
from pathlib import Path
import selectors
import secrets
import signal
import subprocess
import time
import uuid

HERE = Path(__file__).resolve().parent
CACHE = Path('/home/capstone-study/stage_c')
LABEL = 'org.capstone.stage_c'
AGENT_TAG = 'capstone-ctf-agent:prepared'
MAX_COMMAND_OUTPUT = 32768


def random_flag(original):
    left, right = original.find('{'), original.rfind('}')
    if left < 0 or right != len(original)-1 or right-left-1 < 16:
        raise ValueError('No reviewed same-length randomisation for this flag format')
    alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return original[:left+1] + ''.join(secrets.choice(alphabet) for _ in range(right-left-1)) + '}'


class InfrastructureError(RuntimeError):
    pass


def command(args, timeout=60, check=True, limit=65536, stdin_file=None):
    """Bound total process time and retained output, including trickled output."""
    if os.name != 'posix':
        raise InfrastructureError('Container control must run inside Linux WSL')
    start = time.monotonic()
    input_stream = open(stdin_file, 'rb') if stdin_file else None
    try:
        process = subprocess.Popen(args, stdin=input_stream, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    except BaseException:
        if input_stream:
            input_stream.close()
        raise
    output = bytearray()
    total = 0
    timed_out = False
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        while selector.get_map():
            remaining = timeout - (time.monotonic() - start)
            if remaining <= 0:
                timed_out = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                break
            for key, _ in selector.select(min(remaining, .1)):
                chunk = os.read(key.fd, 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                total += len(chunk)
                output.extend(chunk[:max(0, limit-len(output))])
        process.wait(timeout=5)
    finally:
        selector.close()
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        process.stdout.close()
        if input_stream:
            input_stream.close()
    result = {'exit_code': process.returncode, 'output': output.decode('utf-8', errors='replace'),
              'truncated': total > limit, 'timed_out': timed_out,
              'elapsed_seconds': time.monotonic() - start}
    if check and (timed_out or process.returncode):
        raise InfrastructureError(f"Command failed: {args[0:3]}: {result['output'][-2000:]}")
    return result


def docker(*args, **kwargs):
    return command(['docker', *map(str, args)], **kwargs)


def load_task(task_id):
    tasks = json.loads((CACHE/'resolved_tasks.json').read_text())
    development = CACHE/'resolved_development_tasks.json'
    if development.exists():
        tasks += json.loads(development.read_text())
    matches = [task for task in tasks if task['id'] == task_id]
    if len(matches) != 1:
        raise ValueError('Task is not in the reviewed manifest')
    task = matches[0]
    vendor = (CACHE/'vendor'/task.get('vendor_folder', 'CTFTiny')).resolve()
    if vendor.name not in ('CTFTiny', 'NYU_CTF_Bench'):
        raise ValueError('Unreviewed source repository')
    directory = (vendor/task['source_path']).resolve()
    if not directory.is_relative_to(vendor):
        raise ValueError('Task path escapes pinned package cache')
    metadata = json.loads((directory/'challenge.json').read_text())
    if not isinstance(metadata.get('flag'), str) or not metadata['flag']:
        raise ValueError('No supported exact flag checker for this task')
    return task, directory, metadata


def isolated_network():
    return {'internal': True, 'driver': 'bridge', 'driver_opts': {
        'com.docker.network.bridge.gateway_mode_ipv4': 'isolated'}}


def agent_service(image):
    return {'image': image, 'user': '10001:10001', 'working_dir': '/work',
            'environment': {'HOME': '/work', 'TERM': 'xterm'},
            'command': ['sleep', 'infinity'], 'read_only': True, 'cap_drop': ['ALL'],
            'security_opt': ['no-new-privileges:true'], 'dns': ['127.0.0.1'],
            'mem_limit': '1g', 'cpus': 1.0, 'pids_limit': 128,
            'tmpfs': ['/work:rw,exec,nosuid,nodev,size=256m,uid=10001,gid=10001',
                      '/tmp:rw,exec,nosuid,nodev,size=128m,mode=1777'],
            'networks': ['ctfnet'], 'labels': {LABEL: 'agent'}}


def compose_document(original, image_lock, agent_image):
    """Build an allowlisted deployment instead of running upstream Compose directly."""
    allowed = {'image', 'build', 'ports', 'networks', 'volumes', 'restart', 'environment',
               'depends_on', 'command', 'entrypoint', 'user', 'working_dir'}
    services = {}
    networks = {'ctfnet': isolated_network()}
    for name, source in original['services'].items():
        if set(source) - allowed:
            raise ValueError(f'Unreviewed service settings: {set(source)-allowed}')
        mounts = source.get('volumes', [])
        if any(mount != '/var/run/docker.sock:/var/run/docker.sock' for mount in mounts):
            raise ValueError('Unexpected upstream mount; review required')
        if source['image'] not in image_lock:
            raise ValueError('Unpinned target image')
        service = {key: copy.deepcopy(source[key]) for key in
                   ('environment', 'depends_on', 'command', 'entrypoint', 'user', 'working_dir')
                   if key in source}
        service.update(image=image_lock[source['image']], restart='no', cap_drop=['ALL'],
                       cap_add=['CHOWN', 'DAC_OVERRIDE', 'FOWNER', 'FSETID', 'SETGID', 'SETUID',
                                'NET_BIND_SERVICE', 'SYS_CHROOT', 'KILL'],
                       security_opt=['no-new-privileges:true'],
                       mem_limit='1g', cpus=1.0, pids_limit=128, labels={LABEL: 'target'},
                       logging={'driver': 'local', 'options': {'max-size': '10m', 'max-file': '2'}})
        if source['image'].split(':')[0] in ('llmctf/2017q-pwn-pilot',
                'llmctf/2016f-pwn-detective', 'llmctf/2015f-pwn-hipster'):
            # Its legacy PAM/su startup requires the standard audit-write capability.
            service['cap_add'].append('AUDIT_WRITE')
        source_networks = source.get('networks', ['ctfnet'])
        if isinstance(source_networks, list):
            source_networks = dict.fromkeys(source_networks)
        service['networks'] = {}
        for network, settings in source_networks.items():
            networks[network] = isolated_network()
            settings = settings or {}
            if set(settings) - {'aliases'}:
                raise ValueError('Unexpected network settings')
            service['networks'][network] = {'aliases': list(settings.get('aliases', []))}
        services[name] = service
    services['agent'] = agent_service(agent_image)
    result = {'services': services, 'networks': networks}
    assert_no_host_access(result)
    return result


def assert_no_host_access(document):
    for network in document['networks'].values():
        if network != isolated_network():
            raise ValueError('Network is not the reviewed isolated network')
    for service in document['services'].values():
        if any(service.get(key) for key in ('ports', 'volumes', 'privileged', 'devices',
                                           'network_mode', 'pid', 'ipc', 'extra_hosts')):
            raise ValueError('Host access or a published port is forbidden')
        if service.get('cap_drop') != ['ALL']:
            raise ValueError('Capabilities must be explicitly restricted')
        if not set(service.get('networks', [])) <= set(document['networks']):
            raise ValueError('Unexpected network attachment')


class Environment:
    def __init__(self, task_id=None, fixture_document=None, discovery=False):
        import yaml
        self.project = 'csc-' + uuid.uuid4().hex[:12]
        self.directory = CACHE/'trials'/self.project
        self.directory.mkdir(parents=True)
        self.container = None
        self.task_id = task_id
        self.metadata = None
        self.task_directory = None
        self.discovery = discovery
        self.expected_flag = None
        if fixture_document is not None:
            document = fixture_document
            assert_no_host_access(document)
        else:
            _, directory, metadata = load_task(task_id)
            self.metadata, self.task_directory = metadata, directory
            self.expected_flag = metadata['flag'] if discovery else random_flag(metadata['flag'])
            lock = json.loads((CACHE/'image_lock.json').read_text())
            original = yaml.safe_load((directory/'docker-compose.yml').read_text())
            document = compose_document(original, lock['targets'], lock['agent'])
            if not discovery:
                for service in document['services'].values():
                    env = service.get('environment')
                    if isinstance(env, dict):
                        service['environment'] = {key: value.replace(metadata['flag'], self.expected_flag)
                            if isinstance(value, str) else value for key, value in env.items()}
                    elif isinstance(env, list):
                        service['environment'] = [value.replace(metadata['flag'], self.expected_flag) for value in env]
        self.document = document
        self.compose_path = self.directory/'compose.json'
        self.compose_path.write_text(json.dumps(document, indent=2))
        self.compose_path.chmod(0o600)

    def compose(self, *args, **kwargs):
        return docker('compose', '-f', self.compose_path, '-p', self.project, *args, **kwargs)

    def start(self):
        self.compose('create', '--no-build', '--pull', 'never', timeout=90)
        if self.metadata and not self.discovery:
            patches = json.loads((CACHE/'flag_patches.json').read_text())[self.task_id]
            if not patches.get('validated'):
                raise InfrastructureError('Fresh-flag deployment is not validated')
            for patch in patches['files']:
                container = self.compose('ps', '-a', '-q', patch['service'])['output'].strip()
                source = Path(patch['template'])
                data = source.read_bytes()
                if hashlib.sha256(data).hexdigest() != patch['sha256']:
                    raise InfrastructureError('Fresh-flag template no longer matches')
                payload = self.directory/('secret-'+uuid.uuid4().hex)
                from flag_patch import replace_secret
                payload.write_bytes(replace_secret(data, self.metadata['flag'], self.expected_flag))
                os.chown(payload, patch['uid'], patch['gid'])
                payload.chmod(patch['mode'])
                docker('cp', '--archive', payload, container+':'+patch['path'])
        self.compose('start', timeout=90)
        self.container = self.compose('ps', '-q', 'agent')['output'].strip()
        if not self.container:
            raise InfrastructureError('Agent container did not start')
        if self.metadata:
            # Only the explicitly intended starter files enter the agent container.
            for filename in self.metadata.get('files', []):
                source = (self.task_directory/filename).resolve()
                if not source.is_relative_to(self.task_directory) or not source.is_file():
                    raise InfrastructureError('Invalid starter-file path')
                parent = str(Path('/work')/Path(filename).parent)
                self.exec(['mkdir', '-p', parent])
                # Docker cp refuses a read-only rootfs even when /work is writable tmpfs.
                # Stream only intended starter bytes to a process running as the agent user.
                writer = ('import pathlib,sys; p=pathlib.Path(sys.argv[1]); '
                          'p.write_bytes(sys.stdin.buffer.read()); p.chmod(int(sys.argv[2],8))')
                docker('exec', '-i', self.container, 'python3', '-c', writer,
                       str(Path('/work')/filename), oct(source.stat().st_mode & 0o777),
                       stdin_file=source, timeout=30)
            self.exec(['mkdir', '-p', '/work/.cache'])
        return self

    def wait_healthy(self, seconds=20):
        if not self.metadata:
            return
        until = time.monotonic()+seconds
        probe = ('import socket; s=socket.create_connection(('
                 +repr(self.metadata['box'])+','+str(int(self.metadata['internal_port']))
                 +'),timeout=1); s.close()')
        while time.monotonic() < until:
            result = self.exec(['python3', '-c', probe], timeout=3)
            if result['exit_code'] == 0:
                return
            time.sleep(.25)
        raise InfrastructureError('Declared challenge endpoint did not become reachable')

    def exec(self, args, timeout=20):
        if not self.container:
            raise InfrastructureError('Environment is not running')
        return docker('exec', self.container, *args, timeout=timeout, check=False,
                      limit=MAX_COMMAND_OUTPUT)

    def terminal(self, text, remaining):
        seconds = max(.1, min(20, remaining-.25))
        return self.exec(['timeout', '--signal=TERM', '--kill-after=1', f'{seconds:.2f}s',
                          'bash', '-c', text], timeout=min(seconds+.2, remaining))

    def close(self):
        self.compose('down', '--volumes', '--remove-orphans', '--timeout', '2', timeout=30)

    def __enter__(self):
        try:
            return self.start()
        except BaseException:
            self.close()
            raise

    def __exit__(self, *unused):
        self.close()
