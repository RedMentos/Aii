#!/usr/bin/env python3
"""Run117AZ: pinned native C3 JEF/C2->C5/C6 DRAFT-only structural diagnostic.

Six reused public calibration rows. This is NOT a disjoint semantic gate or
Redmi proof. No native inference unless --native is explicitly supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

from v13.common import atomic_write, dumps, file_hash
from v13.config import initialize
from v13.models import ModelManager
from tests.integration_step2_utility import installed_links
from scripts import p2x_disjoint_receiver_trainset as p2x
from scripts import jef_c3_c5_c6_operator_cli as cli

FIXTURE_SHA256 = 'eab8867accaf4171e1ebdedf8b7ee26bd9986402ddcc357e048a6706814789fa'
IDS = (
    'P2X06D1534EC02BC098', 'P2X105BDD7A19CAD5E7',
    'P2X36256DD9CA5F1F72', 'P2X3BE98ADF5D778AEA',
    'P2X07A890737C492706', 'P2X0B3A43C1282AA991',
)
ACTIONS = ('A', 'A', 'B', 'B', 'NONE', 'NONE')
MODEL = 'LFM2.5-350M-QAD-Q4_0.gguf'
MODEL_SHA256 = cli.C3_SHA256
RUNNER_SHA256 = cli.RUNNER_SHA256
SCHEMA = 'v13.run117az.native_jef_route_draft.v1'


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def rows():
    original = p2x.fixtures()
    p2x.validate(original)
    calibration = [r for r in original if r['partition'] == 'calibration']
    selected = []
    for action in ('A', 'B', 'NONE'):
        selected.extend(sorted((r for r in calibration if r['oracle_action'] == action),
                               key=lambda r: r['id'])[:2])
    if tuple(r['id'] for r in selected) != IDS or tuple(r['oracle_action'] for r in selected) != ACTIONS:
        raise ValueError('FROZEN_CALIBRATION_IDS_CHANGED')
    frozen = [{
        'id': r['id'], 'domain': r['domain'], 'policy_source': r['b2_source'],
        'sheet_source': r['b1_source'], 'current': r['current'],
        'oracle_action': r['oracle_action'],
    } for r in selected]
    if _sha(json.dumps(frozen, sort_keys=True, separators=(',', ':')).encode('utf-8')) != FIXTURE_SHA256:
        raise ValueError('FROZEN_FIXTURE_SHA_CHANGED')
    return frozen


def installed_binding(installed):
    models = ModelManager(installed)
    model_path = models.path_for('C3_LANGUAGE')
    runner_path = installed/'bin/llama-server'
    model_hash, runner_hash = file_hash(model_path), file_hash(runner_path)
    if model_hash != MODEL_SHA256 or runner_hash != RUNNER_SHA256:
        raise ValueError('NATIVE_MODEL_OR_RUNNER_SHA_RED')
    if models.revision('C3_LANGUAGE') != '657e078c94084481950a2d555a941481f715536b':
        raise ValueError('NATIVE_MODEL_REVISION_RED')
    return {'model_sha256': model_hash, 'runner_sha256': runner_hash,
            'model_revision': models.revision('C3_LANGUAGE')}


def _audit_home(home, expected):
    # Inert coordinator: no queued task may be dispatched during this audit.
    runtime = cli.Runtime(home)
    try:
        messages = runtime.store.rows(
            "SELECT text,status FROM messages WHERE role='assistant' ORDER BY id")
        live = runtime.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status IN ('FINAL','OUTPUT_COMMITTED')")['n']
        actions = runtime.store.rows('SELECT kind FROM actions ORDER BY id')
        return {'assistant_messages': len(messages),
                'all_messages_source_action': all(m['text'] == expected for m in messages),
                'message_statuses': [m['status'] for m in messages],
                'live_output_count': live,
                'action_kinds': [a['kind'] for a in actions]}
    finally:
        runtime.close()


def run(work, installed, out, *, native=False):
    if out.exists():
        raise FileExistsError('FRESH_RAW_DIRECTORY_REQUIRED')
    if work.exists() and any(work.iterdir()):
        raise FileExistsError('FRESH_WORK_DIRECTORY_REQUIRED')
    out.mkdir(parents=True)
    work.mkdir(parents=True, exist_ok=True)
    report = {
        'schema': SCHEMA, 'status': 'INCOMPLETE', 'fixture_sha256': FIXTURE_SHA256,
        'row_ids': list(IDS), 'native_requested': native,
        'native_c3_calls': 0, 'native_body_calls': 0, 'native_c2_calls': 0,
        'native_jef_calls': 0, 'model_free': not native,
        'age0': 'RECORD_ONLY', 'step2': 'UTILITY_FAIL', 'b3': 'NO_PROMOTION',
        'body_jepa': 'UNAVAILABLE', 'world_jepa_authority': 'SHADOW',
        'jepa_weight': 0, 'redmi_measured': False,
        'output_committed': False, 'tool_dispatches': 0,
        'learning_authority': 0, 'delivery_authority': 0,
        'whole_system_complete': False, 'rows': [],
    }
    try:
        selected = rows()
        if native:
            report['binding'] = installed_binding(installed)
        for i, row in enumerate(selected):
            home = work / ('case_%02d' % i)
            initialize(home)
            if native:
                installed_links(home, installed)
            source = {k: row[k] for k in ('id', 'domain', 'policy_source',
                                           'sheet_source', 'current')}
            # CLI requires `project`, not the fixture's `id`.
            source['project'] = source.pop('id')
            input_path = work / ('input_%02d.json' % i)
            input_raw = json.dumps(source, sort_keys=True).encode('utf-8')
            input_path.write_bytes(input_raw)
            result = cli.run(home, input_path, 'native' if native else 'synthetic_exact',
                             operator_opt_in=True, callback_opt_in=True,
                             route_shadow=True)
            audit = _audit_home(home, row['oracle_action'])
            item = {
                'id': row['id'], 'expected_action': row['oracle_action'],
                'input_sha256': _sha(input_raw),
                'source_hashes': {k: _sha(source[k].encode('utf-8'))
                                  for k in ('policy_source', 'sheet_source', 'current')},
                'cli': result, 'store_audit': audit,
                'formatter_exact': result.get('model_formatter_status') == 'FORMATTER_MATCH_SHADOW',
            }
            # Keep each failed attempt durable even if a later row fails.
            atomic_write(out / ('row_%02d.json' % i), dumps(item) + '\n')
            report['rows'].append(item)
            report['native_c3_calls'] += int(result.get('native_model_called') is True)
        report['formatter_exact_count'] = sum(int(x['formatter_exact']) for x in report['rows'])
        structural = all(
            x['cli'].get('status') == 'SHADOW_DRAFT_PREFLIGHT_READY'
            and x['cli'].get('route_shadow_status') == cli.JEF_C2_ROUTE_READY
            and x['cli'].get('c6_status') == 'NEEDS_REAL_TTY_APPROVAL'
            and x['cli'].get('preflight_only') is True
            and x['cli'].get('no_live_output') is True
            and x['cli'].get('source_only_fallback') == (not x['formatter_exact'])
            and x['cli'].get('delivery_authority') == 0
            and x['cli'].get('learning_authority') == 0
            and x['cli'].get('tool_dispatches') == 0
            and x['cli'].get('output_committed') is False
            and x['cli'].get('real_tty_approved') is False
            and x['store_audit']['assistant_messages'] == 1
            and x['store_audit']['all_messages_source_action']
            and x['store_audit']['live_output_count'] == 0
            and x['store_audit']['action_kinds'] == ['TEXT_REPORT']
            for x in report['rows']) and len(report['rows']) == 6
        if native:
            structural = structural and report['native_c3_calls'] == 6 and all(
                x['cli'].get('native_final') is True
                and x['cli'].get('native_process_reaped') is True
                and x['cli'].get('actual_model') == MODEL
                and x['cli'].get('native_model_sha256') == MODEL_SHA256
                and x['cli'].get('runner_sha256') == RUNNER_SHA256
                for x in report['rows'])
        else:
            structural = structural and report['native_c3_calls'] == 0
        report['status'] = ('STRUCTURAL_GREEN_NO_PROMOTION' if structural
                            else 'STRUCTURAL_RED_NO_PROMOTION')
    except BaseException as exc:
        report['status'] = 'STRUCTURAL_RED_NO_PROMOTION'
        report['error_type'] = type(exc).__name__
        report['error_message'] = str(exc)[:320]
    finally:
        atomic_write(out/'report.json', dumps(report) + '\n')
        print(dumps({'status': report['status'], 'native_requested': native,
                     'native_c3_calls': report['native_c3_calls'],
                     'rows': len(report['rows']),
                     'formatter_exact_count': report.get('formatter_exact_count')}))
    return report['status'] == 'STRUCTURAL_GREEN_NO_PROMOTION'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--installed', type=Path)
    p.add_argument('--native', action='store_true')
    a = p.parse_args(argv)
    if a.native and a.installed is None:
        p.error('--installed required for --native')
    return 0 if run(a.work, a.installed, a.out, native=a.native) else 2


if __name__ == '__main__':
    raise SystemExit(main())
