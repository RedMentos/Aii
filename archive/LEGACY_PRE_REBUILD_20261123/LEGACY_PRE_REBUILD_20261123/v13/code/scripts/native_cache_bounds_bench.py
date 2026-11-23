#!/usr/bin/env python3
"""G6B: llama-server RSS and latency with b10964 default cache flags vs V13 bounds.

Same base flags as v13/runners.py (-c 2048 -np 1 -b/-ub 128 -ngl 0 --no-warmup).
Workload per arm: three interleaved conversations (A1 B1 C1 A2 ...), greedy,
fixed answer length, so the host prompt cache and context checkpoints are both
exercised. Each arm uses a fresh server. Linux evidence only, never Redmi RSS.
  python3 scripts/native_cache_bounds_bench.py --server BIN --model ROLE=GGUF ... --out DIR
"""
import argparse
import hashlib
import http.client
import json
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13.runners import native_cache_args  # noqa: E402

# Bounded arm = exactly what the runtime passes with BOOT defaults.
ARMS = {'b10964_default': [], 'v13_bounded': native_cache_args({})}
TOPICS = ('a small bakery that is planning its weekly bread orders',
          'a hiking club that is choosing a route for a rainy weekend',
          'a school library that is reorganising its science shelves')
STEPS = ('Describe the situation in three sentences and name one open problem.',
         'Add one new constraint that makes the problem harder and explain why.',
         'Propose two options and list one cost of each option.',
         'Choose one option and say what you would check first.',
         'Something unexpected happens. Describe it and how it changes the plan.',
         'Summarise every decision made so far as a short numbered list.',
         'Name the riskiest assumption in the plan and how to test it cheaply.',
         'Write a final two-sentence note to the people involved.')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while block := f.read(1 << 20):
            h.update(block)
    return h.hexdigest()


def status_kib(pid):
    out = {}
    for line in Path(f'/proc/{pid}/status').read_text().splitlines():
        key, _, rest = line.partition(':')
        if key in ('VmRSS', 'VmHWM'):
            out[key] = int(rest.split()[0])
    return out


def request(port, body, timeout=600):
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout)
    conn.request('POST', '/v1/chat/completions', json.dumps(body), {'Content-Type': 'application/json'})
    resp = conn.getresponse(); data = json.loads(resp.read()); conn.close()
    if resp.status != 200:
        raise RuntimeError(f'HTTP {resp.status}: {data}')
    return data


def wait_ready(port, proc, deadline):
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError('server exited %s' % proc.returncode)
        try:
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=2); conn.request('GET', '/health')
            if conn.getresponse().status == 200:
                return
        except OSError:
            pass
        time.sleep(.25)
    raise TimeoutError('server not ready')


def run_arm(server, model, arm, threads, answer_tokens, log_path, topics=TOPICS, steps=STEPS):
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]
    cmd = [server, '-m', str(model), '--host', '127.0.0.1', '--port', str(port), '-c', '2048', '-np', '1',
           '-t', str(threads), '-tb', str(threads), '-b', '128', '-ub', '128', '-ngl', '0', '--no-warmup',
           '--no-webui'] + ARMS[arm]
    with open(log_path, 'wb') as log:
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        try:
            wait_ready(port, proc, time.monotonic()+180)
            rows = [dict(turn=0, conversation=None, **status_kib(proc.pid))]
            history = {c: [] for c in range(len(topics))}
            for step, text in enumerate(steps, 1):
                for c, topic in enumerate(topics):
                    messages = [{'role': 'system', 'content': 'You are planning with ' + topic + '. Answer briefly.'}]
                    messages += history[c] + [{'role': 'user', 'content': text}]
                    t0 = time.monotonic()
                    data = request(port, {'messages': messages, 'max_tokens': answer_tokens, 'temperature': 0,
                                          'seed': 13, 'cache_prompt': True, 'id_slot': 0,
                                          'chat_template_kwargs': {'enable_thinking': False}})
                    wall = time.monotonic()-t0
                    answer = data['choices'][0]['message']['content']
                    history[c] += [{'role': 'user', 'content': text}, {'role': 'assistant', 'content': answer}]
                    t = data.get('timings', {})
                    rows.append(dict(turn=step, conversation=c, wall_ms=round(wall*1000, 1),
                                     prompt_n=t.get('prompt_n'), prompt_ms=t.get('prompt_ms'),
                                     cache_n=t.get('cache_n'), predicted_n=t.get('predicted_n'),
                                     answer_sha256=hashlib.sha256(answer.encode()).hexdigest(),
                                     **status_kib(proc.pid)))
            return {'cmd_flags': cmd[3:], 'rows': rows}
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait()


def summarise(rows):
    turns = [r for r in rows if r['turn']]
    return {'rss_start_mib': round(rows[0]['VmRSS']/1024, 1), 'rss_end_mib': round(rows[-1]['VmRSS']/1024, 1),
            'hwm_end_mib': round(rows[-1]['VmHWM']/1024, 1),
            'hwm_growth_mib': round((rows[-1]['VmHWM']-rows[0]['VmHWM'])/1024, 1),
            'prompt_tokens_total': sum(r['prompt_n'] or 0 for r in turns),
            'cached_tokens_total': sum(r['cache_n'] or 0 for r in turns),
            'prompt_ms_total': round(sum(r['prompt_ms'] or 0 for r in turns), 1),
            'wall_ms_total': round(sum(r['wall_ms'] for r in turns), 1)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--server', required=True); ap.add_argument('--model', action='append', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--answer-tokens', type=int, default=48)
    ap.add_argument('--workload', choices=('interleaved', 'single'), default='interleaved',
                    help='single = one conversation of 24 turns (one user, the runtime pattern)')
    ap.add_argument('--arm', action='append', default=[], help='extra NAME=flag,flag,... arm')
    a = ap.parse_args()
    for spec in a.arm:
        name, _, flags = spec.partition('=')
        ARMS[name] = flags.split(',')
    topics, steps = (TOPICS, STEPS) if a.workload == 'interleaved' else (TOPICS[:1], STEPS*3)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=False)
    models = dict(m.split('=', 1) for m in a.model)
    report = {'schema': 'v13-native-cache-bounds-v1', 'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'platform': platform.platform(), 'server_sha256': sha(a.server),
              'models_sha256': {r: sha(p) for r, p in models.items()}, 'arms': ARMS,
              'workload': {'kind': a.workload, 'conversations': len(topics), 'turns_each': len(steps), 'answer_tokens': a.answer_tokens,
                           'threads': a.threads}, 'script_sha256': sha(__file__),
              'phone_measured': False, 'canonical_gate_pass': False, 'results': {}}
    for role, model in models.items():
        report['results'][role] = {}
        for arm in ARMS:
            run = run_arm(a.server, model, arm, a.threads, a.answer_tokens, out/f'{role}-{arm}.log', topics, steps)
            run['summary'] = summarise(run['rows'])
            report['results'][role][arm] = run
            print(role, arm, json.dumps(run['summary']), flush=True)
        d = report['results'][role]['b10964_default']['rows']
        for k in ARMS:
            if k != 'b10964_default':
                b = report['results'][role][k]['rows']
                same = sum(x['answer_sha256'] == y['answer_sha256'] for x, y in zip(d[1:], b[1:]))
                report['results'][role][k]['answers_identical_to_default'] = f'{same}/{len(d)-1}'
    report['finished'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    (out/'report.json').write_text(json.dumps(report, indent=1)+'\n')


if __name__ == '__main__':
    main()
