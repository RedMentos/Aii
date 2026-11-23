#!/usr/bin/env python3
"""Offline evidence transport diagnostics for recorded STEP2 native rows.

No inference, production decisions, repair, source copying or gate promotion.
Audit source inventory, producer quotes and actual C3 messages are distinct.
Only a complete source with a matching hash can authenticate source excerpts.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.utility import score_decision, paired_utility
from analyze_step2_proof import task_score


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def reject(value):
        raise ValueError('nonfinite JSON constant: ' + value)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=reject)


def ref_key(ref):
    if not isinstance(ref, dict):
        return None
    sid, sha = ref.get('source_id'), ref.get('sha256')
    start, end = ref.get('char_start'), ref.get('char_end')
    if (not isinstance(sid, str) or not sid or not isinstance(sha, str)
            or len(sha) != 64 or type(start) is not int or type(end) is not int
            or not 0 <= start <= end or ref.get('modality') != 'text'):
        return None
    return sid, sha, start, end, 'text'


class Sources:
    """Authenticate recorded spans against full text, never against a fixture oracle."""
    def __init__(self, entries):
        self.full = {}
        self.errors = []
        self.invalid_ids = set()
        self.entries = entries if isinstance(entries, list) else []
        for entry in self.entries:
            ref = entry.get('source_ref') if isinstance(entry, dict) else None
            key = ref_key(ref)
            text = entry.get('text') if isinstance(entry, dict) else None
            if key is None or not isinstance(text, str) or key[3] - key[2] != len(text):
                self.errors.append('invalid source inventory entry')
                if isinstance(ref, dict):
                    self.invalid_ids.add(ref.get('source_id'))
                continue
            sid, sha, start, end, _ = key
            if start == 0 and end == len(text) and hashlib.sha256(text.encode()).hexdigest() == sha:
                previous = self.full.get(sid)
                if previous is not None and previous != (sha, text):
                    self.invalid_ids.add(sid)
                    self.errors.append('conflicting complete source: ' + sid)
                else:
                    self.full[sid] = (sha, text)
        # A conflicting excerpt cannot coexist with an authenticated full source.
        for entry in self.entries:
            if not isinstance(entry, dict):
                continue
            key = ref_key(entry.get('source_ref'))
            if key and key[0] in self.full:
                sha, text = self.full[key[0]]
                if key[1] != sha or key[3] > len(text) or entry.get('text') != text[key[2]:key[3]]:
                    self.invalid_ids.add(key[0])
                    self.errors.append('conflicting source span: ' + key[0])

    def resolve(self, ref):
        key = ref_key(ref)
        if key is None:
            return {'status': 'INVALID_REF', 'source_ref': ref, 'text': None}
        sid, sha, start, end, _ = key
        if sid in self.invalid_ids:
            return {'status': 'INVALID_SOURCE', 'source_ref': ref, 'text': None}
        complete = self.full.get(sid)
        if complete is None:
            return {'status': 'UNAVAILABLE_COMPLETE_SOURCE', 'source_ref': ref, 'text': None}
        actual_sha, text = complete
        if sha != actual_sha or end > len(text):
            return {'status': 'INVALID_SOURCE', 'source_ref': ref, 'text': None}
        return {'status': 'VERIFIED', 'source_ref': ref, 'text': text[start:end]}


def consumer_payload(row):
    messages = row.get('consumer_messages')
    if not isinstance(messages, list):
        return None, 'UNAVAILABLE'
    users = [m for m in messages if isinstance(m, dict) and m.get('role') == 'user']
    if len(users) != 1 or not isinstance(users[0].get('content'), str):
        return None, 'AMBIGUOUS_MESSAGES'
    try:
        value = strict_json(users[0]['content'])
    except (ValueError, TypeError):
        return None, 'INVALID_MESSAGE_JSON'
    if (not isinstance(value, dict) or not isinstance(value.get('current_source'), str)
            or not isinstance(value.get('analysts'), list)):
        return None, 'INVALID_MESSAGE_SCHEMA'
    return value, 'RECORDED'


def native_status(metrics):
    value = metrics.get('status') if isinstance(metrics, dict) else None
    return value if isinstance(value, str) and value else 'UNAVAILABLE'


def analyze_row(row, fixture):
    sources = Sources(row.get('source_evidence'))
    consumer, consumer_status = consumer_payload(row)
    event = row.get('event') or {}
    current = sources.resolve(event.get('source_ref'))
    current_bound = bool(consumer and current['status'] == 'VERIFIED'
                         and consumer['current_source'] == current['text']
                         and fixture and fixture.get('current') == current['text'])
    offers = row.get('offers') if isinstance(row.get('offers'), list) else []
    selected = row.get('focal_offer_ids')
    selected_offers = None
    if isinstance(selected, list) and len(selected) == len(set(selected)):
        by_id = {o.get('packet_id'): o for o in offers if isinstance(o, dict)}
        if len(by_id) == len(offers) and all(pid in by_id for pid in selected):
            selected_offers = [by_id[pid] for pid in selected]
    analysts = consumer['analysts'] if consumer else []
    alignment = (selected_offers is not None and len(selected_offers) == len(analysts)
                 and all(isinstance(a, dict) and a.get('role') == o.get('role')
                         for o, a in zip(selected_offers, analysts)))
    analyst_by_id = {o.get('packet_id'): a for o, a in zip(selected_offers or [], analysts)} if alignment else {}
    providers = []
    for offer in offers:
        if not isinstance(offer, dict):
            continue
        context_refs = offer.get('context_source_refs')
        contexts = [sources.resolve(ref) for ref in context_refs] if isinstance(context_refs, list) else []
        prior = [item for item in contexts if item['status'] == 'VERIFIED' and fixture
                 and item['text'] == fixture.get('prior')]
        context_verified = isinstance(context_refs, list) and all(c['status'] == 'VERIFIED' for c in contexts)
        evidence_refs = offer.get('evidence_refs')
        provenance = offer.get('provenance')
        quotes = []
        for ref in evidence_refs if isinstance(evidence_refs, list) else []:
            quote = sources.resolve(ref)
            key = ref_key(ref)
            contained = bool(key and isinstance(provenance, list) and any(
                (p := ref_key(parent)) and p[:2] == key[:2] and p[4] == key[4]
                and p[2] <= key[2] <= key[3] <= p[3] for parent in provenance))
            quote['provenance_contains_span'] = contained
            if quote['status'] == 'VERIFIED' and not contained:
                quote['status'] = 'UNBOUND_PROVENANCE'
            declared = (offer.get('offer') or {}).get('quotes')
            quote['declared_by_producer'] = isinstance(declared, list) and quote['text'] in declared
            if quote['status'] == 'VERIFIED' and not quote['declared_by_producer']:
                quote['status'] = 'UNDECLARED_QUOTE'
            quotes.append(quote)
        prior_ids = {p['source_ref']['source_id'] for p in prior}
        prior_quotes = [q for q in quotes if q['status'] == 'VERIFIED' and q['source_ref']['source_id'] in prior_ids]
        analyst = analyst_by_id.get(offer.get('packet_id'))
        actual_quotes = analyst.get('verified_quotes') if isinstance(analyst, dict) else None
        producer_verified = isinstance(evidence_refs, list) and all(q['status'] == 'VERIFIED' for q in quotes)
        delivered = (isinstance(actual_quotes, list) and producer_verified
                     and actual_quotes == [q['text'] for q in quotes])
        if analyst is None or any(q['status'].startswith('UNAVAILABLE') for q in quotes):
            transport = 'UNAVAILABLE'
        elif not producer_verified:
            transport = 'INVALID_SOURCE_EVIDENCE'
        else:
            transport = 'MATCH' if delivered else 'MISMATCH'
        prior_consumed = bool(delivered and prior_quotes)
        providers.append({
            'packet_id': offer.get('packet_id'), 'role': offer.get('role'),
            'native_status': native_status(offer.get('native_metrics')),
            'context_sources': contexts, 'context_verified': context_verified,
            'registered_prior_available': bool(prior) if context_verified and fixture else None,
            'verified_quotes': quotes, 'prior_quote_count': len(prior_quotes),
            'quote_evidence_verified': producer_verified,
            'selected_for_consumer': offer.get('packet_id') in (selected or []),
            'consumer_quote_transport': transport,
            'prior_quote_consumed': prior_consumed if delivered else None,
            'available_prior_not_quoted': bool(prior) and producer_verified and not prior_quotes,
            'hypothesis': offer.get('offer'),
        })
    raw = row.get('raw_answer')
    answer = None
    try:
        if not isinstance(raw, str) or not raw:
            raise ValueError('absent answer')
        answer = strict_json(raw)
        syntax = 'VALID_JSON'
    except (ValueError, TypeError):
        syntax = 'INVALID_JSON' if isinstance(raw, str) and raw else 'UNAVAILABLE'
    oracle = fixture.get('oracle') if fixture else None
    score = score_decision(raw, oracle) if isinstance(oracle, dict) and syntax != 'UNAVAILABLE' else None
    invalid_decision = bool(score and any(x.startswith('invalid:') for x in score['contradictions']))
    output_status = syntax if syntax != 'VALID_JSON' else 'INVALID_DECISION_SCHEMA' if invalid_decision else 'VALID_DECISION_SCHEMA' if score else 'UNAVAILABLE_DECISION_SCHEMA'
    errors = [k for k, ok in (score or {}).get('field_checks', {}).items() if not ok]
    current_rule_errors = [k for k in errors if k == 'action' or k.endswith(('.remaining', '.eligible'))]
    current_entity_errors = [k for k in errors if k.endswith(('.cost', '.days', '.local'))]
    selected_providers = [p for p in providers if p['selected_for_consumer']]
    no_verified_prior = (alignment and all(p['consumer_quote_transport'] == 'MATCH' for p in selected_providers)
                         and not any(p['prior_quote_consumed'] for p in selected_providers))
    unsupported_rule_values = False
    if (fixture and fixture.get('temporal_mode') == 'RETAIN_PRIOR_RULES' and current_bound
            and no_verified_prior and output_status == 'VALID_DECISION_SCHEMA'):
        unsupported_rule_values = (answer['action'] != 'UNKNOWN' or any(
            option['remaining'] is not None or option['eligible'] is not None for option in answer['options']))
    return {
        'fixture': row.get('fixture'), 'variant': row.get('variant'), 'recorded_status': row.get('status'),
        'source_inventory_errors': sources.errors, 'authenticated_complete_sources': len(sources.full),
        'consumer_messages_status': consumer_status, 'current_source_bound': current_bound,
        'consumer_offer_alignment': alignment, 'providers': providers,
        'native_consumer_status': native_status(row.get('native_consumer_metrics')),
        'output_status': output_status, 'strict_score': score,
        'recorded_action': answer.get('action') if isinstance(answer, dict) else None,
        'recorded_score_matches': row.get('score') == score if score else None,
        'task_assertions': task_score(row),
        'current_source_entity_field_errors': current_entity_errors if current_bound else None,
        'current_override_rule_errors': current_rule_errors if current_bound and fixture and fixture.get('temporal_mode') == 'CURRENT_EXPLICIT_OVERRIDE' else None,
        'no_verified_prior_quote_in_consumer': no_verified_prior if alignment else None,
        'rule_values_without_verified_prior_quote': unsupported_rule_values,
        'raw_answer': raw,
    }


def analyze(proof):
    fixtures = proof.get('fixtures') or []
    fixture_map = {f['id']: f for f in fixtures if isinstance(f, dict) and isinstance(f.get('id'), str)}
    variants = [v[0] for v in proof.get('variant_spec', []) if isinstance(v, (list, tuple)) and v and isinstance(v[0], str)]
    rows = proof.get('rows') if isinstance(proof.get('rows'), list) else []
    expected = {(fid, v) for fid in fixture_map for v in variants}
    observed = [(r.get('fixture'), r.get('variant')) for r in rows if isinstance(r, dict)]
    coverage_known = bool(expected) and len(fixtures) == len(fixture_map) and len(variants) == len(set(variants))
    complete = coverage_known and len(observed) == len(expected) and len(set(observed)) == len(observed) and set(observed) == expected
    analyzed = [analyze_row(r, fixture_map.get(r.get('fixture'))) for r in rows if isinstance(r, dict)]
    def metric(predicate, eligible=lambda r: True, applicable=lambda r: True):
        population = [r for r in analyzed if applicable(r)]
        cohort = [r for r in population if eligible(r)]
        return {'count': sum(bool(predicate(r)) for r in cohort), 'denominator': len(cohort),
                'unavailable_rows': len(population) - len(cohort),
                'inapplicable_rows': len(analyzed) - len(population)}
    score_rows = [dict(r, score=a['strict_score']) for r, a in zip(rows, analyzed) if a['strict_score'] is not None]
    paired = paired_utility(score_rows, list(fixture_map)) if coverage_known and len(score_rows) == len(rows) else None
    finite_elapsed = [r['elapsed_s'] for r in rows if isinstance(r, dict) and type(r.get('elapsed_s')) in (int, float) and math.isfinite(r['elapsed_s'])]
    measured_rss = [r['sampled_native_peak_rss_bytes'] for r in rows if isinstance(r, dict)
                    and type(r.get('sampled_native_peak_rss_bytes')) is int and r['sampled_native_peak_rss_bytes'] >= 0]
    providers = [p for row in analyzed for p in row['providers']]
    action_values = [r['recorded_action'] for r in analyzed if isinstance(r['recorded_action'], str)]
    return {
        'proof_kind': 'STEP2_SOURCE_TRANSPORT_ANALYSIS', 'analysis_version': 1,
        'source_status': proof.get('status'), 'status': 'COMPLETE_COHORT_DIAGNOSTIC' if complete else 'PARTIAL_COHORT_DIAGNOSTIC',
        'gate_promotion': False, 'complementarity_proven': False,
        'uses_real_weights_recorded': proof.get('uses_real_weights'), 'phone_measured_recorded': proof.get('phone_measured'),
        'coverage': {'complete': complete, 'expected_rows': len(expected) if coverage_known else None,
                     'recorded_rows': len(rows), 'unique_rows': len(set(observed)),
                     'missing_pairs': [list(p) for p in sorted(expected - set(observed))],
                     'unexpected_pairs': [list(p) for p in set(observed) - expected],
                     'duplicate_rows': len(observed) - len(set(observed))},
        'metrics': {
            'invalid_json': metric(lambda r: r['output_status'] == 'INVALID_JSON', lambda r: r['output_status'] != 'UNAVAILABLE'),
            'invalid_decision_schema': metric(lambda r: r['output_status'] == 'INVALID_DECISION_SCHEMA', lambda r: r['strict_score'] is not None),
            'producer_prior_available_not_quoted': metric(lambda r: any(p['available_prior_not_quoted'] for p in r['providers']), lambda r: bool(r['providers']) and all(p['context_verified'] and p['quote_evidence_verified'] for p in r['providers'])),
            'consumer_quote_transport_mismatch': metric(lambda r: any(p['consumer_quote_transport'] == 'MISMATCH' for p in r['providers']), lambda r: r['consumer_offer_alignment'] and all(p['consumer_quote_transport'] in {'MATCH', 'MISMATCH'} for p in r['providers'] if p['selected_for_consumer'])),
            'current_source_entity_errors': metric(lambda r: bool(r['current_source_entity_field_errors']), lambda r: r['current_source_bound'] and r['output_status'] == 'VALID_DECISION_SCHEMA'),
            'current_override_rule_errors': metric(lambda r: bool(r['current_override_rule_errors']), lambda r: r['current_override_rule_errors'] is not None and r['output_status'] == 'VALID_DECISION_SCHEMA', lambda r: fixture_map.get(r['fixture'], {}).get('temporal_mode') == 'CURRENT_EXPLICIT_OVERRIDE'),
            'rule_values_without_verified_prior_quote': metric(lambda r: r['rule_values_without_verified_prior_quote'], lambda r: r['current_source_bound'] and r['consumer_offer_alignment'] and r['output_status'] == 'VALID_DECISION_SCHEMA', lambda r: fixture_map.get(r['fixture'], {}).get('temporal_mode') == 'RETAIN_PRIOR_RULES'),
            'native_consumer_final': metric(lambda r: r['native_consumer_status'] == 'FINAL', lambda r: r['native_consumer_status'] != 'UNAVAILABLE'),
            'native_provider_final': {'count': sum(p['native_status'] == 'FINAL' for p in providers),
                                      'denominator': sum(p['native_status'] != 'UNAVAILABLE' for p in providers),
                                      'unavailable_offers': sum(p['native_status'] == 'UNAVAILABLE' for p in providers)},
            'elapsed_seconds': {'sum_recorded': sum(finite_elapsed), 'denominator': len(finite_elapsed), 'unavailable_rows': len(rows)-len(finite_elapsed)},
            'sampled_native_peak_rss_bytes': {'max_recorded': max(measured_rss) if measured_rss else None,
                                              'denominator': len(measured_rss), 'unavailable_rows': len(rows)-len(measured_rss)},
            'recorded_actions': {'counts': {value: action_values.count(value) for value in sorted(set(action_values))},
                                 'denominator': len(action_values), 'unavailable_rows': len(analyzed)-len(action_values)},
        },
        'existing_strict_paired_utility': paired, 'rows': analyzed,
        'claim_limits': [
            'Complete coverage is not semantic quality, source-unchanged proof, activation authority or canonical gate completion.',
            'Prior availability requires authenticated recorded full source text; absent or partial-only source inventory is unavailable.',
            'A verified prior quote proves its exact span reached the consumer, not that all required rules were covered.',
            'Available prior not quoted is a producer transport observation, not a causal claim about final output.',
            'Current override errors use the unchanged preregistered scorer; no values are copied into production.',
            'Missing native metrics remain unavailable; source report uses_real_weights is recorded metadata, not independently inferred.',
            'Recorded source hashes/spans and quote provenance are checked for internal consistency; the analyzer does not reopen the original Store.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('proof', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    raw = args.proof.read_bytes()
    result = analyze(strict_json(raw))
    result['source_report_sha256'] = hashlib.sha256(raw).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': result['status'], 'coverage': result['coverage'], 'gate_promotion': False}))


if __name__ == '__main__':
    main()
