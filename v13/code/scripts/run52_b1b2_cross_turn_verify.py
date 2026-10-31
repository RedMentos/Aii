#!/usr/bin/env python3
"""Independent Run52 original B1/B2 cross-turn native packet/source replay."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

from scripts.run47_jef_c3_typed_receiver_verify import (
    MODELS, RUNNER_SHA, NEGATIVE, canonical, parse, sha)

FIXTURE_SHA = '5cc8783dedbb201a0a8b86763c99dc23130e1d126a603cf0afcac33d8b985f3b'
PROJECTS = ('Harbor', 'Willow', 'Cobalt')
ROLES = ('B1_DETAIL', 'B2_GIST')
OVERRIDES = {'b1_recent_source_chars': 960, 'b2_state_slots': 4,
             'b2_context_chars': 768, 'b2_quote_select': 'pointer',
             'b2_offer_body_state': False, 'offer_quote_context_chars': 400,
             'offer_quote_min_chars': 80, 'body_question_scope': 'rule_decision',
             'observer_tokens': 160, 'threads': 2, 'seed': 13, 'temperature': 0}


def require(ok, code):
    if not ok:
        raise ValueError('RUN52_REPLAY_' + code)


def lexical_b1(summary, oracle):
    if type(summary) is not str:
        return 0
    if oracle['choice'] == 'NONE':
        return int(bool(re.search(r'\b(?:none|neither|no eligible|no option qualifies)\b', summary, re.I)))
    return int(bool(re.search(r'\b(?:option\s*)?' + oracle['choice'] + r'\b', summary, re.I))
               and bool(re.search(r'(?<!\d)' + str(oracle['remaining']) + r'(?!\d)', summary)))


def prior_transport(offer, ref, source):
    for evidence in offer.get('evidence_refs', []):
        if (evidence.get('source_id') == ref['source_id']
                and evidence.get('sha256') == ref['sha256']
                and 0 <= evidence.get('char_start', -1) < evidence.get('char_end', -1) <= len(source)):
            excerpt = source[evidence['char_start']:evidence['char_end']]
            if any(t in excerpt.lower() for t in ('budget', 'deadline', 'local-only')):
                return 1
    return 0


def replay(report_path, fixture_path):
    raw = Path(fixture_path).read_bytes()
    require(sha(raw) == FIXTURE_SHA, 'FIXTURE_SHA')
    fixture = parse(raw)
    require(fixture.get('schema') == 'v13.run52.b1b2_cross_turn_seed479.v1'
            and fixture.get('seed') == 479
            and [f.get('id') for f in fixture.get('fixtures', [])] == list(PROJECTS), 'FIXTURE')
    report = parse(Path(report_path).read_bytes())
    require(report.get('schema') == 'v13.run52.b1b2_cross_turn_native_result.v1'
            and report.get('fixture_sha256') == FIXTURE_SHA
            and report.get('seed') == 479 and report.get('registered') is True
            and report.get('negative_gates') == NEGATIVE, 'REGISTRATION')
    binding = report.get('binding', {})
    require(binding.get('model_sha256') == MODELS and
            binding.get('runner_sha256') == RUNNER_SHA, 'NATIVE_BINDING')
    rows = report.get('rows')
    require(type(rows) is list and len(rows) <= 3
            and [r.get('fixture') for r in rows] == list(PROJECTS[:len(rows)]), 'ROW_ORDER')
    manifest = report.get('row_sha256')
    require(type(manifest) is dict and set(manifest) == {r['fixture'] for r in rows}, 'ROW_MANIFEST')
    b1 = b2 = 0
    reasons = []
    for row in rows:
        f = next(f for f in fixture['fixtures'] if f['id'] == row['fixture'])
        require(manifest[f['id']] == sha(canonical(row)), 'ROW_SHA')
        require(row.get('prior_sha256') == sha(f['prior'].encode())
                and row.get('current_sha256') == sha(f['current'].encode())
                and row.get('oracle_visible_to_native') is False, 'SOURCES')
        if row.get('status') != 'RECORDED':
            require(row.get('b1_signal') == 0 and row.get('b2_prior_transport') == 0, 'RED_SCORE_ZERO')
            reasons.append(f['id'] + ':' + str(row.get('status')))
            continue
        prior, current = row.get('prior_source_ref'), row.get('current_source_ref')
        for ref, source in ((prior, f['prior']), (current, f['current'])):
            require(type(ref) is dict and ref.get('sha256') == sha(source.encode())
                    and ref.get('char_start') == 0 and ref.get('char_end') == len(source)
                    and ref.get('modality') == 'text', 'SOURCE_REF')
        require(prior['source_id'] != current['source_id']
                and row.get('config_overrides') == OVERRIDES, 'CONFIG')
        offers = row.get('offers')
        require(type(offers) is list and len(offers) == 4
                and [(x['stage'], x['role']) for x in offers] ==
                [('prior', 'B1_DETAIL'), ('prior', 'B2_GIST'),
                 ('current', 'B1_DETAIL'), ('current', 'B2_GIST')], 'OFFER_ORDER')
        event_ids = {}
        for item in offers:
            stage, role = item['stage'], item['role']
            event_ids.setdefault(stage, item['event_id'])
            require(event_ids[stage] == item['event_id'], 'EVENT_PAIR')
            ref, source = (prior, f['prior']) if stage == 'prior' else (current, f['current'])
            p, q = item.get('offer'), item.get('query_packet')
            require(type(p) is dict and type(q) is dict
                    and p.get('role') == role and p.get('event_id') == item['event_id']
                    and p.get('based_on_state_version') == 0
                    and p.get('query_packet_id') == q.get('packet_id')
                    and q.get('event_id') == item['event_id']
                    and q.get('target_role') == role and q.get('probe_only') is True
                    and q.get('based_on_state_version') == 0
                    and q.get('source_refs') == [ref]
                    and q.get('goal') == source
                    and q.get('source_view_width_chars') == (240 if role == 'B1_DETAIL' else 960)
                    and p.get('brain_generation_id') == q.get('brain_generation_id')
                    and p.get('native_metrics', {}).get('status') == 'FINAL', 'QUERY_OFFER')
            require(p.get('model_revision') == binding.get('model_revisions', {}).get(role), 'MODEL_REVISION')
            if stage == 'current':
                require(any(x.get('source_id') == prior['source_id']
                            for x in q.get('context_source_refs', [])), 'PRIOR_CONTEXT_PRESENT')
            evidence = item.get('evidence')
            require(type(evidence) is list and len(evidence) == len(p.get('evidence_refs', [])), 'EVIDENCE_COUNT')
            for refrow, ev in zip(p['evidence_refs'], evidence):
                require(ev.get('source_ref') == refrow, 'EVIDENCE_REF')
                bound = next(((base, src) for base, src in ((prior, f['prior']), (current, f['current']))
                              if refrow.get('source_id') == base['source_id']
                              and refrow.get('sha256') == base['sha256']), None)
                require(bound is not None, 'EVIDENCE_SCOPE')
                base, src = bound
                a, b = refrow.get('char_start'), refrow.get('char_end')
                require(type(a) is int and type(b) is int
                        and 0 <= a < b <= len(src)
                        and ev.get('text') == src[a:b], 'EVIDENCE_EXACT')
        require(event_ids['prior'] != event_ids['current'], 'EVENT_ISOLATION')
        require(row.get('processes_reaped') is True
                and type(row.get('process_releases')) is list
                and len(row['process_releases']) >= 4
                and all(x.get('process_reaped') is True for x in row['process_releases']), 'PROCESS_REAP')
        current_offers = {x['role']: x['offer'] for x in offers if x['stage'] == 'current'}
        scored_b1 = lexical_b1(current_offers['B1_DETAIL']['offer']['summary'], f['oracle'])
        scored_b2 = prior_transport(current_offers['B2_GIST'], prior, f['prior'])
        require(row.get('b1_signal') == scored_b1
                and row.get('b2_prior_transport') == scored_b2, 'SCORE')
        b1 += scored_b1
        b2 += scored_b2
    structural = len(rows) == 3 and not reasons
    signal = structural and b1 >= 2 and b2 >= 2 and report.get('installed_binding_unchanged') is True
    if structural:
        require(report.get('b1b2_signal') is signal and report.get('status') ==
                ('B1B2_CROSS_TURN_SIGNAL_ONLY' if signal else 'UTILITY_FAIL'), 'AGGREGATE')
    else:
        require(report.get('status') in ('STRUCTURAL_RED', 'RUNNING'), 'STRUCTURAL_STATUS')
    return {'schema': 'v13.run52.independent_replay.v1',
            'structural_valid': structural, 'b1b2_signal': signal,
            'b1_lexical_signal': b1, 'b2_prior_rule_transport': b2,
            'rows': len(rows), 'native_calls_expected': 12,
            'reasons': reasons, 'negative_gates': NEGATIVE,
            'scope': 'LINUX_NATIVE_B1_B2_SOURCE_TRANSPORT_ONLY_NO_BODY_JEPA_OR_STEP2_PROMOTION'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--fixture', type=Path, required=True)
    a = p.parse_args()
    result = replay(a.report, a.fixture)
    print(json.dumps(result, sort_keys=True), flush=True)
    if not result['b1b2_signal']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()