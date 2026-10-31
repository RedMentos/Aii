#!/usr/bin/env python3
"""Run112 actual B2_GIST native earlier-source offer to C3 native SHADOW plan.

One disjoint public synthetic case. No production Runtime._turn integration,
learning, user-visible answer, tool action or gate promotion.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from v13.common import atomic_write, dumps, file_hash
from v13.config import DEFAULTS
from v13.models import ModelManager
from v13.runtime import Runtime
from v13.store import audit_closed
from v13 import context_os as ctxos
from scripts.run111_c3_b2_context_native import (
    _prepare_home, _plan, score, SCHEMA, SYSTEM)

FIXTURE_SHA = '243b709273d96d7844e1d097a63d1de13cf37922112c52dd80465ec3a7f7e517'
B2_SHA = '57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf'
B2_REV = '8fea620810c4afa23dd6443f999a48574c1611a3'
C3_SHA = '3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'
C3_REV = '657e078c94084481950a2d555a941481f715536b'
RUNNER_SHA = '79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39'
SEED = 907


def fixture(path):
    from hashlib import sha256
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != FIXTURE_SHA:
        raise ValueError('RUN112_FROZEN_FIXTURE_SHA_RED')
    row = json.loads(raw)
    if (set(row) != {'schema','seed','project','prior','current','quote','expected'}
            or row['schema'] != 'v13.run112.real_b2_c3_seed907.v1'
            or type(row['seed']) is not int or row['seed'] != SEED
            or row['project'] != 'Nova' or row['expected'] != 'A'
            or row['quote'] not in row['prior']
            or not row['prior'].startswith('Project Nova archived ')
            or not row['current'].startswith('Project Nova latest ')):
        raise ValueError('RUN112_FROZEN_FIXTURE_FIELDS_RED')
    return row


def _reaped(releases):
    return (bool(releases)
            and any(x.get('before') is not None for x in releases)
            and all(x.get('process_reaped') is True for x in releases))


def _cfg():
    return DEFAULTS | {
        'seed': SEED, 'temperature': 0.0,
        'observer_tokens': 256, 'observer_seconds': 120,
        'answer_tokens': 32, 'deadline_seconds': 180,
        'history_turns': 0, 'memory_top_k': 0,
        'learning_mode': 'RECORD_ONLY', 'b2_control': 'two_body',
        'b2_quote_select': 'pointer', 'offer_quote_context_chars': 400,
        'b2_offer_body_state': False, 'b2_state_slots': 2,
        'b2_context_chars': 1500, 'memory_threshold': 0.0,
    }


def run(fixture_path, work, out, *, installed=None):
    row = fixture(fixture_path)
    work, out = Path(work), Path(out)
    if work.exists() or out.exists():
        raise FileExistsError('RUN112_FRESH_WORK_AND_REPORT_REQUIRED')
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    installed = Path(installed).resolve() if installed is not None else None
    native = installed is not None
    report = {
        'schema': 'v13.run112.real_b2_to_c3_native.v1',
        'fixture_sha256': FIXTURE_SHA, 'seed': SEED,
        'native_b2': native, 'native_c3': native,
        'status': 'INCOMPLETE', 'expected': row['expected'],
        'b2_offers': [], 'b2_native_calls': 0, 'c3_native_calls': 0,
        'prior_verified_for_c3': False, 'source_decision_correct': None,
        'age0': 'RECORD_ONLY', 'step2': 'UTILITY_FAIL',
        'b3': 'NO_PROMOTION', 'body_jepa': 'UNAVAILABLE',
        'world_jepa': 'SHADOW', 'jepa_weight': 0,
        'redmi_measured': False, 'whole_system_complete': False,
        'output_committed': False, 'tool_dispatches': 0,
        'learning_authority': 0, 'delivery_authority': 0,
    }
    path = out / 'report.json'
    def save():
        atomic_write(path, dumps(report))
    save()
    home = work / 'home'
    if native:
        models = ModelManager(installed)
        if (file_hash(models.path_for('B2_GIST')) != B2_SHA
                or models.revision('B2_GIST') != B2_REV
                or file_hash(models.path_for('C3_LANGUAGE')) != C3_SHA
                or models.revision('C3_LANGUAGE') != C3_REV
                or file_hash(installed / 'bin/llama-server') != RUNNER_SHA):
            report['status'] = 'STRUCTURAL_RED'
            report['error'] = 'PINNED_B2_C3_RUNNER_RED'
            save()
            return report
    _prepare_home(home, installed, _cfg())
    runtime = Runtime(home)
    try:
        if not native:
            plan = _plan(runtime, dict(row, id=row['project']), 400)
            report['preflight_plan_mode'] = plan['plan_mode']
            report['prior_verified_for_c3'] = row['prior'] in '\n'.join(
                m['content'] for m in plan['messages'])
            if not report['prior_verified_for_c3']:
                raise ValueError('SYNTHETIC_PREFLIGHT_PRIOR_MISSING')
            report['status'] = 'MODEL_FREE_PREFLIGHT_PASS'
        else:
            prior = runtime.store.event(runtime.session, row['prior'])
            report['prior_source_ref'] = prior['source_ref']
            for phase in ('prior', 'current'):
                event = prior if phase == 'prior' else runtime.store.event(
                    runtime.session, row['current'])
                if phase == 'current':
                    current = event
                    report['current_source_ref'] = current['source_ref']
                before = len(runtime.pool.release_history)
                item = {'phase': phase, 'status': 'INCOMPLETE',
                        'source_ref': event['source_ref']}
                report['b2_offers'].append(item)
                save()
                try:
                    offer = runtime.cognition.offer(
                        'B2_GIST', event, 0, time.monotonic() + 120)
                    item['packet_id'] = offer['packet_id']
                    item['model_revision'] = offer.get('model_revision')
                    item['native_metrics'] = offer.get('native_metrics')
                    item['quotes'] = offer.get('offer', {}).get('quotes')
                    item['evidence_refs'] = offer.get('evidence_refs')
                    item['native_final'] = (
                        offer.get('native_metrics', {}).get('status') == 'FINAL')
                    report['b2_native_calls'] += 1
                finally:
                    runtime.pool.unload()
                    item['process_reaped'] = _reaped(
                        runtime.pool.release_history[before:])
                    item['status'] = ('RECORDED' if item.get('native_final')
                                      and item.get('model_revision') == B2_REV
                                      and item['process_reaped']
                                      and item.get('native_metrics', {}).get('actual_model')
                                      == 'Qwen3.5-0.8B-Q4_0.gguf'
                                      else 'STRUCTURAL_RED')
                    save()
                if item['status'] != 'RECORDED':
                    raise ValueError('B2_NATIVE_OFFER_STRUCTURAL_RED')
                if phase == 'current':
                    current_offer = offer
            rendered = runtime.cognition.analyst_context([current_offer], current, 0)
            verified = rendered[0]['verified_quotes']
            prior_quotes = [v for v in verified
                            if v['source_ref']['source_id'] == prior['source_ref']['source_id']
                            and row['prior'] in v['text']]
            report['prior_verified_for_c3'] = bool(prior_quotes)
            report['verified_quotes'] = verified
            if not prior_quotes:
                raise ValueError('B2_DID_NOT_SELECT_EARLIER_PRIOR_RULES')
            volatile = [('HYPOTHESES', '\nSource-bound hypotheses, not facts: ', rendered)]
            plan = ctxos.controller(runtime).plan(
                current['event_id'], 'C3_LANGUAGE', SYSTEM,
                volatile, [], row['current'],
                provenance=[current['source_ref'], prior['source_ref']])
            if plan['applied'] is not False or plan['plan']['mode'] != 'SHADOW':
                raise ValueError('C3_CONTEXT_AUTHORITY_RED')
            messages = plan['messages']
            content = '\n'.join(m['content'] for m in messages)
            if (row['prior'] not in content or 'Maximum deadline:' not in content
                    or 'Required local-only:' not in content
                    or '"expected"' in dumps(messages)):
                raise ValueError('C3_SOURCE_PLAN_INCOMPLETE_OR_ORACLE_LEAK')
            from hashlib import sha256
            report['c3_input_sha256'] = sha256(dumps(messages).encode()).hexdigest()
            report['c3_messages'] = messages
            save()
            before = len(runtime.pool.release_history)
            try:
                runner = runtime.pool.get('C3_LANGUAGE')
                report['c3_native_calls'] = 1
                output = ''.join(runner.generate(
                    messages, runtime.cancel_event, time.monotonic() + 90,
                    32, SCHEMA, seed=SEED))
                metrics = dict(runner.last_metrics)
                report['c3_output'] = output
                report['c3_native_metrics'] = metrics
                report['c3_score'] = score(output, row['expected'])
                report['source_decision_correct'] = bool(report['c3_score']['correct'])
            finally:
                runtime.pool.unload()
                report['c3_process_reaped'] = _reaped(
                    runtime.pool.release_history[before:])
                save()
            if (metrics.get('status') != 'FINAL'
                    or metrics.get('actual_model') != 'LFM2.5-350M-QAD-Q4_0.gguf'
                    or not report['c3_process_reaped']):
                raise ValueError('C3_NATIVE_STRUCTURAL_RED')
            report['status'] = 'NATIVE_B2_C3_STRUCTURAL_PASS'
    except Exception as exc:
        report['status'] = 'STRUCTURAL_RED'
        report['error_type'] = type(exc).__name__
        report['error'] = str(exc)[:320]
    finally:
        try:
            report['no_live_output'] = (
                runtime.store.one(
                    "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
                    "AND status IN ('FINAL','OUTPUT_COMMITTED')")['n'] == 0
                and runtime.store.one('SELECT COUNT(*) AS n FROM actions')['n'] == 0)
            if not report['no_live_output']:
                report['status'] = 'STRUCTURAL_RED'
        except Exception:
            report['status'] = 'STRUCTURAL_RED'
        runtime.close()
        try:
            report['closed_store_ok'] = bool(audit_closed(home)['ok'])
        except Exception:
            report['closed_store_ok'] = False
        if not report['closed_store_ok']:
            report['status'] = 'STRUCTURAL_RED'
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
    print(dumps({'status': result['status'],
                 'b2_native_calls': result['b2_native_calls'],
                 'c3_native_calls': result['c3_native_calls'],
                 'prior_verified_for_c3': result['prior_verified_for_c3'],
                 'source_decision_correct': result['source_decision_correct']}))
    return 0 if result['status'] in (
        'MODEL_FREE_PREFLIGHT_PASS', 'NATIVE_B2_C3_STRUCTURAL_PASS') else 2


if __name__ == '__main__':
    raise SystemExit(main())
