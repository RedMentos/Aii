#!/usr/bin/env python3
"""Run111 disjoint C3 native use of real Context OS B2-source transport.

The B2 pointer selector is explicitly SYNTHETIC; only C3 is native. This is
an isolated SHADOW research experiment, not a Runtime._turn change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
from types import SimpleNamespace
from unittest.mock import patch

from v13.common import atomic_write, dumps, file_hash
from v13.config import initialize, save_config, DEFAULTS
from v13.runtime import Runtime
from v13.store import audit_closed
from v13 import context_os as ctxos

FIXTURE_SHA = '3683f38a0c7ca00411c623d223a4b965de2f6203eb314750d163e4a9426cbb42'
MODEL_SHA = '3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'
RUNNER_SHA = '79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39'
MODEL_REVISION = '657e078c94084481950a2d555a941481f715536b'
MODEL_NAME = 'LFM2.5-350M-QAD-Q4_0.gguf'
SEED = 881
ARMS = ('WIDE_400', 'NARROW_0')
SCHEMA = {'type': 'object', 'additionalProperties': False,
          'required': ['choice'],
          'properties': {'choice': {'type': 'string', 'enum': ['A', 'B', 'NONE']}}}
SYSTEM = ('Use only the earlier source-verified project rules and current options. '
          'A valid option must meet every earlier budget, deadline and local-only rule. '
          'If neither option is valid, select NONE. Return only JSON with one key '
          'choice containing A, B or NONE. Do not invent rules or extra facts.')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('RUN111_DUPLICATE_JSON')
        out[key] = value
    return out


def score(raw, expected):
    try:
        value = json.loads(raw, object_pairs_hook=_unique,
                           parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    except (ValueError, TypeError):
        return {'valid': False, 'correct': 0, 'choice': None}
    valid = (type(value) is dict and set(value) == {'choice'}
             and type(value['choice']) is str
             and value['choice'] in ('A', 'B', 'NONE'))
    return {'valid': valid, 'correct': int(valid and value['choice'] == expected),
            'choice': value['choice'] if valid else None}


def fixture(path):
    raw = Path(path).read_bytes()
    if sha(raw) != FIXTURE_SHA:
        raise ValueError('RUN111_FIXTURE_SHA_RED')
    data = json.loads(raw)
    rows = data.get('rows', [])
    if (data.get('schema') != 'v13.run111.c3_prior_rules_seed881.v1'
            or type(data.get('seed')) is not int or data['seed'] != SEED
            or [r.get('id') for r in rows] != ['Tilia', 'Zephyr', 'Oriole', 'Sable']
            or [r.get('expected') for r in rows] != ['B', 'B', 'A', 'NONE']):
        raise ValueError('RUN111_FIXTURE_COHORT_RED')
    for row in rows:
        if (set(row) != {'id', 'prior', 'current', 'quote', 'expected'}
                or row['quote'] not in row['prior']
                or not row['prior'].startswith('Project ' + row['id'] + ' ')
                or not row['current'].startswith('Project ' + row['id'] + ' ')):
            raise ValueError('RUN111_FIXTURE_SOURCE_RED')
    return rows


def _prepare_home(home, installed, cfg):
    initialize(home)
    save_config(home, cfg)
    if installed is not None:
        for name in ('models', 'bin'):
            dest = home / name
            if dest.is_symlink():
                dest.unlink()
            elif dest.exists():
                shutil.rmtree(dest)
            dest.symlink_to(installed / name, target_is_directory=True)
        shutil.copyfile(installed / 'config/models.json', home / 'config/models.json')


def _fake_b2(row):
    def generate(messages, *args, **kwargs):
        payload = json.loads(messages[-1]['content'])
        choices = [x['id'] for x in payload.get('quote_choices', [])
                   if x.get('text') == row['quote']]
        if len(choices) != 1:
            raise ValueError('RUN111_EXACT_B2_POINTER_MISSING')
        return iter([dumps({'summary': 'Source-bound archived policy.',
                            'quotes': choices, 'uncertainty': '',
                            'needs_reentry': False})])
    return SimpleNamespace(last_metrics={'status': 'FINAL', 'synthetic_b2': True},
                           generate=generate)


def _plan(runtime, row, width):
    runtime.cfg.update({'b2_state_slots': 2, 'b2_context_chars': 1500,
                        'b2_control': 'two_body', 'b2_quote_select': 'pointer',
                        'offer_quote_context_chars': width,
                        'memory_threshold': 0.0})
    with patch.object(runtime.pool, 'get', return_value=_fake_b2(row)):
        prior = runtime.store.event(runtime.session, row['prior'])
        runtime.cognition.offer('B2_GIST', prior, 0, time.monotonic() + 30)
        current = runtime.store.event(runtime.session, row['current'])
        offer = runtime.cognition.offer('B2_GIST', current, 0, time.monotonic() + 30)
    rendered = runtime.cognition.analyst_context([offer], current, 0)
    volatile = [('HYPOTHESES', '\nSource-bound hypotheses, not facts: ', rendered)]
    plan = ctxos.controller(runtime).plan(
        current['event_id'], 'C3_LANGUAGE', SYSTEM,
        volatile, [], row['current'],
        provenance=[current['source_ref'], prior['source_ref']])
    if plan['applied'] is not False or plan['plan']['mode'] != 'SHADOW':
        raise ValueError('RUN111_CONTEXT_AUTHORITY_RED')
    if prior['source_ref'] not in plan['plan']['provenance']:
        raise ValueError('RUN111_PRIOR_PROVENANCE_RED')
    text = '\n'.join(m['content'] for m in plan['messages'])
    if row['quote'] not in text:
        raise ValueError('RUN111_BUDGET_QUOTE_LOST')
    if width == 400:
        if row['prior'] not in text or 'Maximum deadline:' not in text or 'Required local-only:' not in text:
            raise ValueError('RUN111_WIDE_PRIOR_RULES_LOST')
    elif ('Maximum deadline:' in text or 'Required local-only:' in text):
        raise ValueError('RUN111_NARROW_LEAKS_PRIOR_RULES')
    if '"expected"' in dumps(plan['messages']):
        raise ValueError('RUN111_ORACLE_LEAK')
    return {'messages': plan['messages'], 'prior_source_ref': prior['source_ref'],
            'current_source_ref': current['source_ref'],
            'verified_quote': rendered[0]['verified_quotes'][0]['text'],
            'plan_mode': plan['plan']['mode']}


def run(fixture_path, work, out, *, installed=None):
    rows = fixture(fixture_path)
    work, out = Path(work), Path(out)
    if work.exists() or out.exists():
        raise FileExistsError('RUN111_FRESH_WORK_AND_REPORT_REQUIRED')
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    installed = Path(installed).resolve() if installed is not None else None
    native = installed is not None
    report = {'schema': 'v13.run111.c3_prior_rule_ablation.v1',
              'fixture_sha256': FIXTURE_SHA, 'seed': SEED,
              'arms': list(ARMS), 'native_c3': native,
              'synthetic_b2': True, 'body_native_calls': 0,
              'status': 'INCOMPLETE', 'rows': [],
              'age0': 'RECORD_ONLY', 'step2': 'UTILITY_FAIL',
              'b3': 'NO_PROMOTION', 'body_jepa': 'UNAVAILABLE',
              'world_jepa': 'SHADOW', 'jepa_weight': 0,
              'redmi_measured': False, 'whole_system_complete': False,
              'output_committed': False, 'tool_dispatches': 0,
              'learning_authority': 0, 'delivery_authority': 0}
    path = out / 'report.json'
    def save():
        atomic_write(path, dumps(report))
    save()
    if native:
        from v13.models import ModelManager
        models = ModelManager(installed)
        if (file_hash(models.path_for('C3_LANGUAGE')) != MODEL_SHA
                or models.revision('C3_LANGUAGE') != MODEL_REVISION
                or file_hash(installed / 'bin/llama-server') != RUNNER_SHA):
            raise ValueError('RUN111_PINNED_MODEL_OR_RUNNER_RED')
    try:
        for index, row in enumerate(rows):
            order = ARMS if index % 2 == 0 else ARMS[::-1]
            for arm in order:
                width = 400 if arm == 'WIDE_400' else 0
                home = work / (row['id'] + '-' + arm)
                cfg = DEFAULTS | {'seed': SEED, 'temperature': 0.0,
                                  'answer_tokens': 32, 'observer_tokens': 128,
                                  'observer_seconds': 30, 'deadline_seconds': 120,
                                  'history_turns': 0, 'memory_top_k': 0,
                                  'learning_mode': 'RECORD_ONLY',
                                  'b2_quote_select': 'pointer',
                                  'offer_quote_context_chars': width}
                _prepare_home(home, installed, cfg)
                runtime = Runtime(home)
                item = {'id': row['id'], 'arm': arm, 'expected': row['expected'],
                        'status': 'INCOMPLETE', 'native_final': False,
                        'process_reaped': False, 'strict': 0}
                report['rows'].append(item)
                save()
                before = len(runtime.pool.release_history)
                try:
                    planned = _plan(runtime, row, width)
                    item.update(planned)
                    item['messages_sha256'] = sha(dumps(planned['messages']).encode())
                    if native:
                        runner = runtime.pool.get('C3_LANGUAGE')
                        output = ''.join(runner.generate(
                            planned['messages'], runtime.cancel_event,
                            time.monotonic() + 90, 32, SCHEMA, seed=SEED))
                        metrics = dict(runner.last_metrics)
                        item['output'] = output
                        item['output_sha256'] = sha(output.encode())
                        item['score'] = score(output, row['expected'])
                        item['strict'] = item['score']['correct']
                        item['native_final'] = metrics.get('status') == 'FINAL'
                        item['actual_model'] = metrics.get('actual_model')
                    item['status'] = 'RECORDED' if not native else 'INCOMPLETE'
                except Exception as exc:
                    item['error_type'] = type(exc).__name__
                    item['error'] = str(exc)[:240]
                    item['status'] = 'STRUCTURAL_RED'
                finally:
                    try:
                        runtime.pool.unload()
                    except Exception as exc:
                        item['unload_error_type'] = type(exc).__name__
                        item['status'] = 'STRUCTURAL_RED'
                    releases = runtime.pool.release_history[before:]
                    item['process_reaped'] = (
                        bool(releases) and any(x.get('before') is not None for x in releases)
                        and all(x.get('process_reaped') is True for x in releases))
                    try:
                        no_output = (runtime.store.one(
                            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
                            "AND status IN ('FINAL','OUTPUT_COMMITTED')")['n'] == 0
                            and runtime.store.one('SELECT COUNT(*) AS n FROM actions')['n'] == 0)
                        item['no_live_output'] = no_output
                        if not no_output:
                            item['status'] = 'STRUCTURAL_RED'
                    except Exception:
                        item['status'] = 'STRUCTURAL_RED'
                    runtime.close()
                    try:
                        item['closed_store_ok'] = bool(audit_closed(home)['ok'])
                    except Exception:
                        item['closed_store_ok'] = False
                    if not item['closed_store_ok']:
                        item['status'] = 'STRUCTURAL_RED'
                    if native and item['status'] != 'STRUCTURAL_RED':
                        item['status'] = ('RECORDED' if item['native_final']
                                          and item.get('actual_model') == MODEL_NAME
                                          and item['process_reaped']
                                          else 'STRUCTURAL_RED')
                    save()
                if item['status'] != 'RECORDED':
                    raise RuntimeError('RUN111_ROW_STRUCTURAL_RED')
        complete = len(report['rows']) == 8 and all(
            r['status'] == 'RECORDED' for r in report['rows'])
        if not complete:
            raise ValueError('RUN111_INCOMPLETE')
        if native:
            wide = sum(r['strict'] for r in report['rows'] if r['arm'] == 'WIDE_400')
            narrow = sum(r['strict'] for r in report['rows'] if r['arm'] == 'NARROW_0')
            report['scores'] = {'WIDE_400': wide, 'NARROW_0': narrow,
                                'exploratory_signal': wide >= 3 and wide - narrow >= 2}
            report['status'] = ('NATIVE_COMPLETE_EXPLORATORY_SIGNAL'
                                if report['scores']['exploratory_signal']
                                else 'NATIVE_COMPLETE_NO_GAIN')
        else:
            report['status'] = 'MODEL_FREE_PREFLIGHT_PASS'
    except Exception as exc:
        report['status'] = 'STRUCTURAL_RED'
        report['error_type'] = type(exc).__name__
        report['error'] = str(exc)[:300]
    save()
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--installed', type=Path)
    args = p.parse_args()
    result = run(args.fixture, args.work, args.out, installed=args.installed)
    print(dumps({'status': result['status'], 'rows': len(result['rows']),
                 'scores': result.get('scores'), 'native_c3': result['native_c3']}))
    return 0 if result['status'] in (
        'MODEL_FREE_PREFLIGHT_PASS', 'NATIVE_COMPLETE_EXPLORATORY_SIGNAL',
        'NATIVE_COMPLETE_NO_GAIN') else 2


if __name__ == '__main__':
    raise SystemExit(main())
