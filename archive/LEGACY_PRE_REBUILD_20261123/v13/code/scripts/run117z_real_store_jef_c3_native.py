#!/usr/bin/env python3
"""Frozen seed1065 real-Store deterministic JEF -> pinned native C3 two-arm pilot.

Non-delivering SHADOW; no native Body/JEF/C2 or model learning. The typed
candidate is computed from Store USER sources, not fixture oracle injection.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import time

from scripts.run111_c3_b2_context_native import _prepare_home
from scripts.run113b_b1b2_c3_native import _reaped
from scripts.run115j_typed_jef_role_native import C3_FILE, C3_SHA, C3_REV, RUNNER_SHA, SCHEMA
from scripts.run117s_body_complementarity_preflight import SYSTEM as BASE_SYSTEM
from scripts.run117w_c3_arithmetic_native import CONFIG as BASE_CONFIG
from scripts.run47_jef_c3_typed_receiver_native import score
from v13.agi.eligibility import recipe
from v13.common import atomic_write, dumps, file_hash
from v13.jef_span_budget_shadow_candidate import (
    POLICY, OPTION, build_jef_span_budget_shadow,
)
from v13.models import ModelManager
from v13.runtime import Runtime
from v13.store import audit_closed

SEED = 1065
FIXTURE_SHA = 'cb008f27a4d1ef7f0f288419ac276ebb67c8d7958da3c62104994822dd90634d'
IDS = ('Helix', 'Ion', 'Juno', 'Kappa', 'Lumen', 'Mistral')
ARMS = ('RAW_EXACT_SOURCE', 'REAL_STORE_JEF_TYPED')
CONFIG = BASE_CONFIG | {'seed': SEED}
GOOD = ('NATIVE_COMPLETE_EXPLORATORY_REAL_JEF_FORMATTER_GAIN',
        'NATIVE_COMPLETE_NO_REAL_JEF_FORMATTER_GAIN')
RED = 'STRUCTURAL_RED'


def fixture(path):
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != FIXTURE_SHA:
        raise ValueError('RUN117Z_FROZEN_FIXTURE_SHA_RED')
    data = json.loads(raw)
    if (set(data) != {'schema', 'seed', 'arms', 'rows'}
            or data['schema'] != 'v13.run117z.real_jef_native_seed1065.v1'
            or type(data['seed']) is not int or data['seed'] != SEED
            or data['arms'] != list(ARMS)
            or [r.get('id') for r in data['rows']] != list(IDS)):
        raise ValueError('RUN117Z_FROZEN_COHORT_RED')
    for row in data['rows']:
        if set(row) != {'id', 'prior', 'current', 'policy_span', 'option_span', 'oracle'}:
            raise ValueError('RUN117Z_FIXTURE_FIELDS_RED')
        m = POLICY.fullmatch(row['policy_span'])
        opts = list(OPTION.finditer(row['option_span']))
        if (m is None or len(opts) != 2
                or [o[1] for o in opts] != ['A', 'B']
                or row['prior'].count(row['policy_span']) != 1
                or row['current'].count(row['option_span']) != 1
                or not row['prior'].startswith('Project ' + row['id'])
                or not row['current'].startswith('Project ' + row['id'])):
            raise ValueError('RUN117Z_SOURCE_GRAMMAR_RED')
        choices = [{'entity': o[1], 'cost': int(o[2]),
                    'days': int(o[3]), 'local': o[4] == 'true'}
                   for o in opts]
        chosen, evaluated = recipe(int(m[1]), int(m[2]), m[3] == 'true', choices)
        remaining = next((x['remaining'] for x in evaluated
                          if x['entity'] == chosen), None)
        if row['oracle'] != {'choice': chosen, 'remaining': remaining}:
            raise ValueError('RUN117Z_ORACLE_RECIPE_RED')
    return data['rows']


def _pin(installed):
    m = ModelManager(installed)
    if (file_hash(m.path_for('C3_LANGUAGE')) != C3_SHA
            or m.revision('C3_LANGUAGE') != C3_REV
            or file_hash(installed / 'bin/llama-server') != RUNNER_SHA):
        raise ValueError('RUN117Z_PINNED_NATIVE_C3_RED')


def _prompts(runtime, prior, current, row):
    jef = build_jef_span_budget_shadow(runtime, prior, current,
                                       operator_opt_in=True)
    if (jef.get('status') != 'SHADOW_SOURCE_BOUND_JEF_BUDGET_VERIFIED'
            or jef.get('candidate_authority') != 0
            or jef.get('output_committed') is not False
            or jef.get('tool_dispatches') != 0
            or jef.get('learning_authority') != 0
            or jef.get('delivery_authority') != 0):
        raise ValueError('RUN117Z_STORE_JEF_SOURCE_RED')
    # Offline oracle is an assertion only, never included in either prompt.
    if jef['typed_jef_candidate'] != row['oracle']:
        raise ValueError('RUN117Z_REAL_JEF_ORACLE_MISMATCH_RED')
    typed = jef['messages']
    payload = json.loads(typed[1]['content'])
    raw = {'schema': 'v13.run117z.source_only_user_data.v1',
           'source_role': 'UNTRUSTED_EXACT_USER',
           'policy': payload['policy'], 'options': payload['options']}
    base = [{'role': 'system', 'content': BASE_SYSTEM},
            {'role': 'user', 'content': dumps(raw)}]
    for messages in (base, typed):
        if ([m['role'] for m in messages] != ['system', 'user']
                or row['policy_span'] in messages[0]['content']
                or row['option_span'] in messages[0]['content']
                or '"oracle"' in messages[1]['content']):
            raise ValueError('RUN117Z_C3_ROLE_OR_ORACLE_LEAK_RED')
    if 'typed_jef_candidate' in base[1]['content']:
        raise ValueError('RUN117Z_BASE_TYPED_LEAK_RED')
    return {ARMS[0]: base, ARMS[1]: typed}, jef


def _summarize(report):
    scores = {arm: 0 for arm in ARMS}
    counts = {arm: 0 for arm in ARMS}
    if (len(report['rows']) != 6 or report['native_c3_calls'] != 12
            or report['deterministic_jef_calls'] != 6):
        return RED
    for index, row in enumerate(report['rows']):
        if (row['id'] != IDS[index] or row.get('status') != 'RECORDED'
                or row.get('closed_store_ok') is not True
                or row.get('no_live_output') is not True
                or len(row.get('arms', [])) != 2
                or set(x.get('arm') for x in row['arms']) != set(ARMS)):
            return RED
        for item in row['arms']:
            arm = item['arm']
            if (item.get('status') != 'RECORDED'
                    or item.get('native_final') is not True
                    or item.get('process_reaped') is not True
                    or item.get('native_metrics', {}).get('actual_model') != C3_FILE
                    or type(item.get('score', {}).get('correct')) is not int):
                return RED
            counts[arm] += 1
            scores[arm] += item['score']['correct']
    report['scores'] = scores
    report['recorded_by_arm'] = counts
    if any(counts[a] != 6 for a in ARMS):
        return RED
    signal = scores[ARMS[1]] >= 5 and scores[ARMS[1]] >= scores[ARMS[0]] + 2
    report['exploratory_formatter_signal'] = signal
    return GOOD[0] if signal else GOOD[1]


def run(fixture_path, installed, work, out):
    rows = fixture(fixture_path)
    installed, work, out = Path(installed).resolve(), Path(work), Path(out)
    if work.exists() or out.exists():
        raise FileExistsError('RUN117Z_FRESH_WORK_OUT_REQUIRED')
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    report = {
        'schema': 'v13.run117z.real_store_jef_native.v1',
        'seed': SEED, 'fixture_sha256': FIXTURE_SHA,
        'status': 'INCOMPLETE', 'native_c3': True,
        'native_c3_calls': 0, 'native_body_calls': 0,
        'native_jef_calls': 0, 'native_c2_calls': 0,
        'deterministic_jef_calls': 0, 'source_verified_jef_candidates': 0,
        'scores': {a: 0 for a in ARMS}, 'recorded_by_arm': {},
        'exploratory_formatter_signal': False, 'rows': [],
        'age0': 'RECORD_ONLY', 'step2_exit': 'EVIDENCE_NOT_PASSING',
        'b3': 'NO_PROMOTION', 'body_jepa': 'UNAVAILABLE',
        'world_jepa': 'SHADOW', 'jepa_weight': 0,
        'redmi_measured': False, 'whole_system_complete': False,
        'output_committed': False, 'tool_dispatches': 0,
        'learning_authority': 0, 'delivery_authority': 0,
    }
    def save():
        atomic_write(out / 'report.json', dumps(report))
    save()
    try:
        _pin(installed)
        for index, row in enumerate(rows):
            home = work / row['id']
            _prepare_home(home, installed, CONFIG)
            runtime = Runtime(home)
            entry = {'id': row['id'], 'status': 'INCOMPLETE',
                     'arms': [], 'closed_store_ok': False,
                     'no_live_output': False}
            report['rows'].append(entry)
            save()
            try:
                prior = runtime.store.event(runtime.session, row['prior'])
                current = runtime.store.event(runtime.session, row['current'])
                entry['prior_source_ref'] = prior['source_ref']
                entry['current_source_ref'] = current['source_ref']
                prompts, jef = _prompts(runtime, prior, current, row)
                report['deterministic_jef_calls'] += 1
                report['source_verified_jef_candidates'] += 1
                entry['typed_jef_candidate'] = jef['typed_jef_candidate']
                entry['jef_messages_sha256'] = jef['messages_sha256']
                save()
                order = ARMS[index % 2:] + ARMS[:index % 2]
                for arm in order:
                    messages = prompts[arm]
                    item = {'arm': arm, 'status': 'INCOMPLETE',
                            'messages': messages,
                            'messages_sha256': sha256(dumps(messages).encode()).hexdigest(),
                            'native_final': False, 'process_reaped': False,
                            'score': None}
                    entry['arms'].append(item)
                    save()
                    before = len(runtime.pool.release_history)
                    try:
                        runner = runtime.pool.get('C3_LANGUAGE')
                        report['native_c3_calls'] += 1
                        save()
                        output = ''.join(runner.generate(
                            messages, runtime.cancel_event,
                            time.monotonic() + 120, 96, SCHEMA, seed=SEED))
                        item['output'] = output
                        item['native_metrics'] = dict(runner.last_metrics)
                        item['native_final'] = (
                            item['native_metrics'].get('status') == 'FINAL')
                        item['score'] = score(output, row['oracle'])
                    except Exception as exc:
                        item['error_type'] = type(exc).__name__
                        item['error'] = str(exc)[:280]
                    finally:
                        runtime.pool.unload()
                        item['process_reaped'] = _reaped(
                            runtime.pool.release_history[before:])
                        item['status'] = ('RECORDED' if item['native_final']
                            and item['process_reaped']
                            and item.get('native_metrics', {}).get('actual_model') == C3_FILE
                            else RED)
                        save()
                entry['status'] = ('RECORDED' if all(a['status'] == 'RECORDED'
                                    for a in entry['arms']) else RED)
            except Exception as exc:
                entry['status'] = RED
                entry['error_type'] = type(exc).__name__
                entry['error'] = str(exc)[:280]
            finally:
                try:
                    entry['no_live_output'] = (
                        runtime.store.one('SELECT COUNT(*) AS n FROM actions')['n'] == 0
                        and runtime.store.one('SELECT COUNT(*) AS n FROM messages '
                            "WHERE role='assistant'")['n'] == 0)
                except Exception:
                    entry['no_live_output'] = False
                runtime.close()
                try:
                    entry['closed_store_ok'] = bool(audit_closed(home)['ok'])
                except Exception:
                    entry['closed_store_ok'] = False
                if not entry['closed_store_ok'] or not entry['no_live_output']:
                    entry['status'] = RED
                save()
        report['status'] = _summarize(report)
    except Exception as exc:
        report['status'] = RED
        report['error_type'] = type(exc).__name__
        report['error'] = str(exc)[:280]
    save()
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--installed', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    report = run(args.fixture, args.installed, args.work, args.out)
    print(dumps({'status': report['status'], 'scores': report['scores'],
                 'native_c3_calls': report['native_c3_calls'],
                 'deterministic_jef_calls': report['deterministic_jef_calls']}))
    return 0 if report['status'] in GOOD else 2


if __name__ == '__main__':
    raise SystemExit(main())
