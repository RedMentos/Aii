#!/usr/bin/env python3
"""Preregistered generic enum/arithmetic diagnosis; never STEP2 acceptance or training.

Run only after other frozen native cohorts finish. A fresh output directory and
isolated server are required. No application configuration or model is changed.
"""
import argparse
from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13.common import atomic_write, file_hash
from v13.memory_server import runtime_library_hashes

LABELS = ['A', 'B', 'NONE', 'UNKNOWN']
ARMS = ['free_json', 'action_only', 'schema_action_first', 'schema_facts_first']
SYSTEM = ('Return JSON only. For a copy task, copy the requested action, remaining and eligible. '
          'For a decision task, remaining is budget minus each cost; eligible is cost <= budget. '
          'Choose the cheapest eligible option, A on a tie; NONE if neither is eligible. '
          'If budget is null, action is UNKNOWN and both remaining and eligible entries are null. '
          'Return fields action (A, B, NONE or UNKNOWN), remaining (two integer/null values), '
          'eligible (two boolean/null values), in A then B order.')


def cases():
    rows = [{'id': 'copy_' + action, 'task': {'task': 'copy', 'action': action,
             'remaining': [9, 5], 'eligible': [True, False]},
             'expected': {'action': action, 'remaining': [9, 5], 'eligible': [True, False]}}
            for action in LABELS]
    for action, budget, costs in [('A', 20, [4, 7]), ('B', 20, [9, 3]),
                                   ('NONE', 2, [3, 4]), ('UNKNOWN', None, [3, 4])]:
        rows.append({'id': 'decision_' + action,
                     'task': {'task': 'decision', 'budget': budget, 'costs': costs},
                     'expected': {'action': action,
                                  'remaining': [None, None] if budget is None else [budget-c for c in costs],
                                  'eligible': [None, None] if budget is None else [c <= budget for c in costs]}})
    return rows


def schema_for(arm):
    action = {'type': 'string', 'enum': LABELS}
    if arm == 'free_json':
        return None
    props = {'action': action}
    if arm != 'action_only':
        props = {'remaining': {'type': 'array', 'minItems': 2, 'maxItems': 2,
                              'items': {'type': ['integer', 'null']}},
                 'eligible': {'type': 'array', 'minItems': 2, 'maxItems': 2,
                             'items': {'type': ['boolean', 'null']}}, 'action': action}
    return {'type': 'object', 'additionalProperties': False,
            'required': list(props), 'properties': props}


def payload_for(prompt, arm, cap=128, seed=13):
    payload = {'prompt': prompt, 'n_predict': cap, 'stream': False, 'temperature': .1,
               'top_k': 50, 'repeat_penalty': 1.05, 'seed': seed, 'cache_prompt': True,
               'id_slot': 0, 'return_tokens': True}
    schema = schema_for(arm)
    if schema is not None:
        payload['json_schema'] = copy.deepcopy(schema)
    # Same sorted serializer as the application, except the deliberate ordering arm.
    wire = json.dumps(payload, ensure_ascii=False, sort_keys=arm != 'schema_facts_first',
                      separators=(',', ':'), allow_nan=False)
    return payload, wire


def score(raw, expected, arm):
    result = {'action_exact': False, 'all_requested_fields_exact': False}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        result['parse_error'] = True
        return result
    result['parsed'] = parsed
    if not isinstance(parsed, dict):
        return result
    result['action_exact'] = parsed.get('action') == expected['action']
    target = {'action': expected['action']} if arm == 'action_only' else expected
    result['all_requested_fields_exact'] = parsed == target
    return result


def post(port, endpoint, wire=None, timeout=90):
    request = urllib.request.Request('http://127.0.0.1:%d%s' % (port, endpoint),
                                     None if wire is None else wire.encode(),
                                     {'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


@contextmanager
def server(binary, model, log, threads=4):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    env = dict(os.environ)
    for key in list(env):
        if key.startswith('V13_MEMORY_') or key == 'LLAMA_API_KEY':
            env.pop(key)
    command = [str(binary), '-m', str(model), '--host', '127.0.0.1', '--port', str(port),
               '-c', '2048', '-np', '1', '-t', str(threads), '-tb', str(threads),
               '-b', '128', '-ub', '128', '-ngl', '0', '--no-warmup', '--no-webui']
    with open(log, 'wb') as handle:
        proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=handle, stderr=handle, env=env)
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    raise RuntimeError('Isolated diagnostic server exited during startup')
                try:
                    if post(port, '/health', timeout=1).get('status') == 'ok':
                        break
                except (OSError, ValueError):
                    pass
                time.sleep(.1)
            else:
                raise TimeoutError('Isolated diagnostic server startup exceeded 60 seconds')
            yield port, command
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait(timeout=3)


def run(binary, model, out, threads=4, concurrent_load='none declared'):
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    binding = {'binary_sha256': file_hash(binary), 'model_sha256': file_hash(model),
               'runtime_libraries_sha256': runtime_library_hashes(binary),
               'script_sha256': file_hash(__file__),
               'runner_source_sha256': file_hash(Path(__file__).parents[1]/'v13/runners.py'),
               'serializer_source_sha256': file_hash(Path(__file__).parents[1]/'v13/common.py')}
    report = {'status': 'RUNNING', 'binding': binding, 'cases': cases(), 'arms': ARMS,
              'planned_calls': 32, 'rows': [], 'phone_measured': False,
              'canonical_gate_pass': False, 'training_or_activation': False,
              'purpose': 'AUTHORED_GENERIC_SCHEMA_DIAGNOSTIC',
              'execution_scope': {'platform': 'CLOUD_LINUX', 'server_threads': threads,
                                  'concurrent_load': concurrent_load,
                                  'latency_comparison_valid': False, 'phone_measured': False},
              'limits': ['No acceptance fixtures consumed.', 'Action-only has a smaller output task.',
                         'Facts-first changes serialization only; no evidence of benefit before results.',
                         'Historical 230M outputs are not a known-good semantic control.']}
    def save():
        atomic_write(out/'report.json', json.dumps(report, ensure_ascii=False, indent=2))
    save()
    try:
        with server(binary, model, out/'server.log', threads) as (port, command):
            report['server_command'] = command
            report['native_props'] = post(port, '/props')
            save()
            for case in report['cases']:
                for arm in ARMS:
                    row = {'case': case['id'], 'arm': arm, 'status': 'STARTED'}
                    system = SYSTEM + (' Return only the action field.' if arm == 'action_only' else '')
                    messages = [{'role': 'system', 'content': system},
                                {'role': 'user', 'content': json.dumps(case['task'], sort_keys=True)}]
                    row['messages'] = messages
                    start = time.monotonic()
                    try:
                        template_wire = json.dumps({'messages': messages, 'add_generation_prompt': True,
                                                    'chat_template_kwargs': {'enable_thinking': False}}, sort_keys=True)
                        row['template_response'] = post(port, '/apply-template', template_wire)
                        payload, wire = payload_for(row['template_response']['prompt'], arm)
                        row['completion_request_wire'] = wire
                        row['schema_properties_wire_order'] = list(json.loads(wire).get('json_schema', {}).get('properties', {}))
                        row['native_response'] = post(port, '/completion', wire)
                        row['raw_answer'] = row['native_response'].get('content', '')
                        row['score'] = score(row['raw_answer'], case['expected'], arm)
                        row['status'] = 'RECORDED'
                    except Exception as exc:
                        row['status'] = 'ERROR'; row['error'] = {'type': type(exc).__name__, 'detail': str(exc)[:400]}
                    row['seconds'] = time.monotonic() - start
                    report['rows'].append(row); save()
        report['server_reaped'] = True
        report['artifacts_unchanged'] = (binding['binary_sha256'] == file_hash(binary)
                                         and binding['model_sha256'] == file_hash(model)
                                         and binding['runtime_libraries_sha256'] == runtime_library_hashes(binary))
        report['status'] = 'DIAGNOSTIC_COMPLETE' if len(report['rows']) == 32 and all(r['status'] == 'RECORDED' for r in report['rows']) and report['artifacts_unchanged'] else 'DIAGNOSTIC_INCOMPLETE'
    except BaseException as exc:
        report['status'] = 'DIAGNOSTIC_INCOMPLETE'
        report['error'] = {'type': type(exc).__name__, 'detail': str(exc)[:400]}
        save(); raise
    save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True); parser.add_argument('--model', required=True)
    parser.add_argument('--out', required=True); parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--concurrent-load', default='none declared')
    args = parser.parse_args()
    result = run(Path(args.binary), Path(args.model), args.out, args.threads, args.concurrent_load)
    print(json.dumps({'status': result['status'], 'calls': len(result['rows'])}))
    return 0 if result['status'] == 'DIAGNOSTIC_COMPLETE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
