"""Free, descriptive cue check (no model, no network beyond the local isolated sandbox). R5-02.

For each F2 task it starts the EnvironmentF2 sandbox (fresh secret, generic alias) and records, as COUNTS
ONLY (no text, no flags), how often the cue words ctf / flag / challenge / csaw (case-insensitive) occur in
what the model could see on its first look:
  - target_first_response: web tasks: `curl -s -i --max-time 10 http://ALIAS:PORT/` (headers + page);
    pwn tasks: the bytes the service sends within 3 s of a TCP connect, before any input (banner);
  - starter_files: each file copied into /work (the vendored bytes), per file;
  - reverse_dns: `getent hosts` of the target's IP address from inside the agent container;
  - agent_context: `hostname`, /etc/hosts and the environment of the agent shell;
  - model_visible_fixed_text: the F2 system prompt, tool descriptions, harness notices and this task's
    prompt (static; the tool NAME submit_flag is counted separately because it is unavoidable).
The targets and files are NOT changed; residual cues are disclosed in F-PROTOCOL (limitations).
Writes /home/capstone-study/stage_f/f2_cue_check.json. Usage: python3 check_f2_cues.py [TASK ...]
"""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'stage_e'))
sys.path.insert(0, str(HERE.parent/'stage_c'))
from environment_f2 import EnvironmentF2  # noqa: E402
from framing_f2 import CUTOFF_NOTICE_F2, SYSTEM_F2, TARGET_ALIAS, TOOLS_F2, task_prompt_f2  # noqa: E402

TASKS = json.loads((HERE/'f_config.json').read_text())['f2']['tasks']
CACHE = Path('/home/capstone-study/stage_f')
WORDS = ('ctf', 'flag', 'challenge', 'csaw')
BANNER = ('import socket,sys,time\n'
          's=socket.create_connection((sys.argv[1],int(sys.argv[2])),timeout=5)\n'
          's.settimeout(0.5)\n'
          'data=b""\nend=time.time()+3\n'
          'while time.time()<end and len(data)<65536:\n'
          '    try:\n'
          '        chunk=s.recv(4096)\n'
          '    except socket.timeout:\n'
          '        continue\n'
          '    if not chunk:\n'
          '        break\n'
          '    data+=chunk\n'
          'sys.stdout.write(data.decode("latin-1"))\n')


def counts(data):
    """Case-insensitive occurrence counts of each cue word in text or bytes."""
    if isinstance(data, str):
        data = data.encode('utf-8', errors='replace')
    low = data.lower()
    return {w: low.count(w.encode()) for w in WORDS}


def fixed_text(task_prompt):
    import trajectory_v2 as T
    tools = ' '.join(t['function']['description'] for t in TOOLS_F2)
    parts = {'system': SYSTEM_F2, 'tool_descriptions': tools, 'cutoff_notice': CUTOFF_NOTICE_F2,
             'unparsed_call_notice': T.UNPARSED_CALL_NOTICE, 'elision_placeholder': T.ELIDED,
             'task_prompt': task_prompt}
    result = {k: counts(v) for k, v in parts.items()}
    result['task_prompt_flag_only_in_submit_flag'] = (counts(task_prompt.replace('submit_flag', ''))['flag'] == 0)
    return result


def check_task(task_id):
    category = task_id.split('-')[1]
    with EnvironmentF2(task_id) as env:
        env.wait_healthy()
        env.wait_reachable()
        port = str(int(env.metadata['internal_port']))
        if category == 'web':
            first = env.exec(['curl', '-s', '-i', '--max-time', '10', 'http://%s:%s/' % (TARGET_ALIAS, port)],
                             timeout=20)
        else:
            first = env.exec(['python3', '-c', BANNER, TARGET_ALIAS, port], timeout=20)
        files = {}
        for name in env.metadata.get('files', []):
            files[name] = counts((env.task_directory/name).read_bytes())
        address = env.exec(['getent', 'hosts', TARGET_ALIAS])['output'].split()
        reverse = env.exec(['getent', 'hosts', address[0]])['output'] if address else ''
        context = env.exec(['bash', '-c', 'hostname; cat /etc/hosts; env'])['output']
        prompt = task_prompt_f2(env.metadata, category)
    return {'target_first_response': dict(counts(first.get('output', '')), bytes=len(first.get('output', '')),
                                          exit_code=first.get('exit_code'),
                                          method='curl /' if category == 'web' else 'tcp banner (3 s, no input)'),
            'starter_files': files,
            'reverse_dns': dict(counts(reverse), resolved=bool(reverse.strip())),
            'agent_context': counts(context),
            'model_visible_fixed_text': fixed_text(prompt)}


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    report = {'alias': TARGET_ALIAS, 'words': list(WORDS), 'counts_only': True, 'tasks': {}}
    for task_id in (sys.argv[1:] or TASKS):
        report['tasks'][task_id] = row = check_task(task_id)
        print(task_id, json.dumps({'target': {w: row['target_first_response'][w] for w in WORDS},
                                   'files': row['starter_files'], 'reverse_dns': row['reverse_dns'],
                                   'agent_context': row['agent_context']}), flush=True)
    (CACHE/'f2_cue_check.json').write_text(json.dumps(report, indent=1)+'\n')
    print('cue check written (descriptive; not a gate)')


if __name__ == '__main__':
    main()
