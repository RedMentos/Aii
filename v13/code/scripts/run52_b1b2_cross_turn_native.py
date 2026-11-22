#!/usr/bin/env python3
"""Run52: actual pinned native B1/B2 two-turn source-transport witness."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import time

from v13.common import atomic_write, dumps
from v13.config import initialize, save_config
from v13.runtime import Runtime
from scripts.run47_jef_c3_typed_receiver_native import CONFIG, NEGATIVE, sha
from tests.integration_step2_utility import installed_artifacts, installed_links

FIXTURE_SHA256 = '5cc8783dedbb201a0a8b86763c99dc23130e1d126a603cf0afcac33d8b985f3b'
PROJECTS = ('Harbor', 'Willow', 'Cobalt')
OVERRIDES = {'b1_recent_source_chars': 960, 'b2_state_slots': 4,
             'b2_context_chars': 768, 'b2_quote_select': 'pointer',
             'b2_offer_body_state': False, 'offer_quote_context_chars': 400,
             'offer_quote_min_chars': 80, 'body_question_scope': 'rule_decision',
             'observer_tokens': 160, 'threads': 2, 'seed': 13, 'temperature': 0}
ROLES = ('B1_DETAIL', 'B2_GIST')


def load_fixture(path):
    raw = Path(path).read_bytes()
    if sha(raw) != FIXTURE_SHA256:
        raise ValueError('RUN52_FIXTURE_SHA')
    data = json.loads(raw)
    if (data.get('schema') != 'v13.run52.b1b2_cross_turn_seed479.v1'
            or data.get('seed') != 479
            or [f.get('id') for f in data.get('fixtures', [])] != list(PROJECTS)):
        raise ValueError('RUN52_COHORT')
    for f in data['fixtures']:
        if (set(f) != {'id', 'prior', 'current', 'oracle'}
                or set(f['oracle']) != {'choice', 'remaining'}
                or f['id'] not in f['prior'] or f['id'] not in f['current']):
            raise ValueError('RUN52_FIXTURE_SHAPE')
    return data


def b1_signal(summary, oracle):
    if type(summary) is not str:
        return 0
    choice = oracle['choice']
    if choice == 'NONE':
        return int(bool(re.search(r'\b(?:none|neither|no eligible|no option qualifies)\b', summary, re.I)))
    return int(bool(re.search(r'\b(?:option\s*)?' + choice + r'\b', summary, re.I))
               and bool(re.search(r'(?<!\d)' + str(oracle['remaining']) + r'(?!\d)', summary)))


def prior_rule_transport(offer, prior_ref, source):
    if type(offer) is not dict:
        return 0
    for ref in offer.get('evidence_refs', []):
        if (ref.get('source_id') == prior_ref['source_id']
                and ref.get('sha256') == prior_ref['sha256']
                and 0 <= ref.get('char_start', -1) < ref.get('char_end', -1) <= len(source)):
            excerpt = source[ref['char_start']:ref['char_end']]
            if any(x in excerpt.lower() for x in ('budget', 'deadline', 'local-only')):
                return 1
    return 0


def run_row(home, installed, fixture):
    initialize(home)
    save_config(home, CONFIG | OVERRIDES)
    installed_links(home, installed)
    r = Runtime(home)
    row = {'fixture': fixture['id'], 'status': 'ERROR',
           'prior_sha256': sha(fixture['prior'].encode()),
           'current_sha256': sha(fixture['current'].encode()),
           'oracle_visible_to_native': False, 'offers': [],
           'process_releases': [], 'processes_reaped': False,
           'b1_signal': 0, 'b2_prior_transport': 0}
    start = time.monotonic()
    try:
        prior = r.store.event(r.session, fixture['prior'])
        current = r.store.event(r.session, fixture['current'])
        row['prior_source_ref'] = prior['source_ref']
        row['current_source_ref'] = current['source_ref']
        row['session_id'] = r.session
        row['config_overrides'] = dict(OVERRIDES)
        for stage, event in (('prior', prior), ('current', current)):
            for role in ROLES:
                offer = r.cognition.offer(role, event, 0, time.monotonic() + 90)
                query_row = r.store.one('SELECT * FROM packets WHERE id=? AND kind=?',
                                        (offer['query_packet_id'], 'QueryPacket'))
                if query_row is None:
                    raise ValueError('RUN52_MISSING_QUERY_PACKET')
                refs = [{'source_ref': ref, 'text': r.store.read_source(ref)}
                        for ref in offer['evidence_refs']]
                row['offers'].append({'stage': stage, 'role': role,
                                      'event_id': event['event_id'],
                                      'offer': offer, 'query_packet': json.loads(query_row['payload']),
                                      'evidence': refs})
                r.pool.unload()
        current_offers = {x['role']: x['offer'] for x in row['offers'] if x['stage'] == 'current'}
        row['b1_signal'] = b1_signal(current_offers['B1_DETAIL']['offer']['summary'], fixture['oracle'])
        row['b2_prior_transport'] = prior_rule_transport(current_offers['B2_GIST'], prior['source_ref'], fixture['prior'])
        row['status'] = ('RECORDED' if len(row['offers']) == 4
                         and all(x['offer']['native_metrics'].get('status') == 'FINAL' for x in row['offers'])
                         else 'STRUCTURAL_FAIL')
    except (Exception, KeyboardInterrupt) as exc:
        row['error_type'] = type(exc).__name__
        row['error'] = str(exc)[:500]
        row['status'] = 'INTERRUPTED' if isinstance(exc, KeyboardInterrupt) else 'ERROR'
    finally:
        try:
            r.close()
        except Exception as exc:
            row['close_error_type'] = type(exc).__name__
            row['status'] = 'STRUCTURAL_FAIL'
        row['process_releases'] = list(r.pool.release_history)
        row['processes_reaped'] = len(row['process_releases']) >= 4 and all(
            x.get('process_reaped') is True for x in row['process_releases'])
        if row['status'] == 'RECORDED' and not row['processes_reaped']:
            row['status'] = 'STRUCTURAL_FAIL'
        if row['status'] != 'RECORDED':
            row['b1_signal'] = row['b2_prior_transport'] = 0
        row['elapsed_seconds'] = round(time.monotonic() - start, 3)
    return row


def run(installed, out, fixture_path):
    data = load_fixture(fixture_path)
    if out.exists():
        raise FileExistsError('RUN52_OUTPUT_EXISTS')
    out.mkdir(parents=True)
    binding = installed_artifacts(installed)
    report = {'schema': 'v13.run52.b1b2_cross_turn_native_result.v1',
              'fixture_sha256': FIXTURE_SHA256, 'seed': 479,
              'binding': binding, 'registered': True, 'rows': [],
              'row_sha256': {}, 'status': 'RUNNING', 'negative_gates': NEGATIVE}
    atomic_write(out / 'report.json', dumps(report))
    for f in data['fixtures']:
        home = out / f['id']
        if home.exists():
            raise FileExistsError('RUN52_HOME_EXISTS')
        row = run_row(home, installed, f)
        report['rows'].append(row)
        report['row_sha256'][f['id']] = sha(dumps(row).encode())
        atomic_write(out / 'report.json', dumps(report))
        print(dumps({'fixture': f['id'], 'status': row['status'],
                     'b1_signal': row['b1_signal'],
                     'b2_prior_transport': row['b2_prior_transport']}), flush=True)
    report['installed_binding_unchanged'] = installed_artifacts(installed) == binding
    structural = all(r['status'] == 'RECORDED' for r in report['rows'])
    b1 = sum(r['b1_signal'] for r in report['rows'])
    b2 = sum(r['b2_prior_transport'] for r in report['rows'])
    report['b1b2_signal'] = (structural and b1 >= 2 and b2 >= 2
                            and report['installed_binding_unchanged'])
    report['status'] = ('B1B2_CROSS_TURN_SIGNAL_ONLY' if report['b1b2_signal']
                        else 'UTILITY_FAIL' if structural else 'STRUCTURAL_RED')
    atomic_write(out / 'report.json', dumps(report))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--fixture', type=Path, required=True)
    a = p.parse_args()
    report = run(a.home, a.out, a.fixture)
    print(dumps({'status': report['status'], 'b1b2_signal': report['b1b2_signal']}))


if __name__ == '__main__':
    main()