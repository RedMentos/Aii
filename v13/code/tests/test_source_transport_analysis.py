import copy
import importlib.util
import json
from pathlib import Path
import unittest

from v13.common import digest
from v13.utility import score_decision

PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'analyze_source_transport.py'
SPEC = importlib.util.spec_from_file_location('source_transport_analysis', PATH)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def source(sid, text):
    return {'source_id': sid, 'sha256': digest(text), 'char_start': 0,
            'char_end': len(text), 'modality': 'text'}


def proof(override=False, quote_prior=False):
    prior = 'Project Atlas. Budget 100 euros. Deadline 5 days. Local-only requirement: true.'
    current = ('Project Atlas. Option A: cost 40 euros, duration 2 days, local true. '
               'Option B: cost 70 euros, duration 7 days, local false.')
    if override:
        current += ' Updated rules: budget 80 euros, deadline 3 days, local-only requirement true.'
    budget = 80 if override else 100
    oracle = {'project': 'Atlas', 'action': 'A', 'options': [
        {'entity': 'A', 'cost': 40, 'days': 2, 'local': True, 'remaining': budget-40, 'eligible': True},
        {'entity': 'B', 'cost': 70, 'days': 7, 'local': False, 'remaining': budget-70, 'eligible': False}]}
    current_ref, prior_ref = source('current', current), source('prior', prior)
    quote = prior if quote_prior else 'Project Atlas.'
    quote_ref = prior_ref if quote_prior else current_ref | {'char_end': len(quote)}
    offer = {'packet_id': 'offer', 'role': 'B2_GIST', 'context_source_refs': [prior_ref],
             'provenance': [current_ref, prior_ref], 'evidence_refs': [quote_ref],
             'offer': {'summary': 'fallible hypothesis', 'quotes': [quote], 'uncertainty': 'high', 'needs_reentry': True},
             'native_metrics': {'status': 'FINAL'}}
    context = {'current_source': current, 'analysts': [{'role': 'B2_GIST', 'hypothesis': offer['offer'], 'verified_quotes': [quote]}]}
    raw = json.dumps(oracle)
    row = {'fixture': 'Atlas', 'variant': 'b2_only', 'status': 'RECORDED', 'event': {'source_ref': current_ref},
           'source_evidence': [{'source_ref': current_ref, 'text': current}, {'source_ref': prior_ref, 'text': prior},
                               {'source_ref': quote_ref, 'text': quote}],
           'offers': [offer], 'focal_offer_ids': ['offer'], 'consumer_messages': [{'role': 'user', 'content': json.dumps(context)}],
           'raw_answer': raw, 'score': score_decision(raw, oracle), 'native_consumer_metrics': {'status': 'FINAL'}, 'elapsed_s': 1.5}
    return {'status': 'RUNNING', 'uses_real_weights': True, 'phone_measured': False,
            'fixtures': [{'id': 'Atlas', 'prior': prior, 'current': current, 'oracle': oracle,
                          'temporal_mode': 'CURRENT_EXPLICIT_OVERRIDE' if override else 'RETAIN_PRIOR_RULES'}],
            'variant_spec': [['b2_only', ['B2_GIST'], 'NO_MESSAGE', False]], 'rows': [row]}


class SourceTransportAnalysis(unittest.TestCase):
    def test_audit_inventory_is_not_consumer_evidence(self):
        p = proof()
        out = m.analyze(p)
        provider = out['rows'][0]['providers'][0]
        self.assertTrue(provider['registered_prior_available'])
        self.assertTrue(provider['available_prior_not_quoted'])
        self.assertEqual(provider['prior_quote_count'], 0)
        self.assertFalse(provider['prior_quote_consumed'])
        self.assertTrue(out['rows'][0]['rule_values_without_verified_prior_quote'])
        self.assertEqual(out['metrics']['producer_prior_available_not_quoted']['count'], 1)

    def test_prior_quote_verified_and_delivered_is_distinct(self):
        out = m.analyze(proof(quote_prior=True))
        provider = out['rows'][0]['providers'][0]
        self.assertTrue(provider['prior_quote_consumed'])
        self.assertEqual(provider['consumer_quote_transport'], 'MATCH')
        self.assertFalse(provider['available_prior_not_quoted'])
        self.assertFalse(out['rows'][0]['rule_values_without_verified_prior_quote'])
        self.assertFalse(out['gate_promotion'])
        self.assertFalse(out['complementarity_proven'])

    def test_source_hash_tamper_never_counts_available(self):
        p = proof()
        p['rows'][0]['source_evidence'][1]['text'] = 'X' * len(p['fixtures'][0]['prior'])
        row = m.analyze(p)['rows'][0]
        self.assertIsNone(row['providers'][0]['registered_prior_available'])
        self.assertEqual(row['providers'][0]['context_sources'][0]['status'], 'UNAVAILABLE_COMPLETE_SOURCE')
        self.assertFalse(row['providers'][0]['available_prior_not_quoted'])

    def test_partial_excerpt_without_full_source_is_unavailable(self):
        p = proof()
        entry = p['rows'][0]['source_evidence'][1]
        entry['text'] = entry['text'][:25]
        entry['source_ref'] = entry['source_ref'] | {'char_end': 25}
        out = m.analyze(p)
        self.assertEqual(out['metrics']['producer_prior_available_not_quoted']['denominator'], 0)
        self.assertEqual(out['metrics']['producer_prior_available_not_quoted']['unavailable_rows'], 1)

    def test_conflicting_excerpt_invalidates_source(self):
        p = proof()
        ref = p['rows'][0]['offers'][0]['context_source_refs'][0] | {'char_start': 15, 'char_end': 20}
        p['rows'][0]['source_evidence'].append({'source_ref': ref, 'text': 'wrong'})
        row = m.analyze(p)['rows'][0]
        self.assertTrue(row['source_inventory_errors'])
        self.assertEqual(row['providers'][0]['context_sources'][0]['status'], 'INVALID_SOURCE')

    def test_quote_requires_provenance_and_producer_declaration(self):
        p = proof(quote_prior=True)
        p['rows'][0]['offers'][0]['provenance'] = [p['rows'][0]['event']['source_ref']]
        row = m.analyze(p)['rows'][0]
        self.assertEqual(row['providers'][0]['verified_quotes'][0]['status'], 'UNBOUND_PROVENANCE')
        self.assertIsNone(row['providers'][0]['prior_quote_consumed'])
        p = proof(quote_prior=True)
        p['rows'][0]['offers'][0]['offer']['quotes'] = ['not the source']
        row = m.analyze(p)['rows'][0]
        self.assertEqual(row['providers'][0]['verified_quotes'][0]['status'], 'UNDECLARED_QUOTE')

    def test_consumer_mismatch_does_not_claim_transport(self):
        p = proof(quote_prior=True)
        message = p['rows'][0]['consumer_messages'][0]
        value = json.loads(message['content'])
        value['analysts'][0]['verified_quotes'] = ['Budget 999 euros.']
        message['content'] = json.dumps(value)
        out = m.analyze(p)
        self.assertEqual(out['metrics']['consumer_quote_transport_mismatch']['count'], 1)
        self.assertIsNone(out['rows'][0]['providers'][0]['prior_quote_consumed'])

    def test_duplicate_roles_align_by_focal_offer_order(self):
        p = proof(quote_prior=True)
        row = p['rows'][0]
        second = copy.deepcopy(row['offers'][0])
        second['packet_id'] = 'second'
        second['context_source_refs'] = []
        second['evidence_refs'] = [row['event']['source_ref'] | {'char_end': len('Project Atlas.')}]
        second['offer']['quotes'] = ['Project Atlas.']
        row['offers'].append(second)
        row['focal_offer_ids'] = ['second', 'offer']
        value = json.loads(row['consumer_messages'][0]['content'])
        value['analysts'].insert(0, {'role': 'B2_GIST', 'verified_quotes': ['Project Atlas.']})
        row['consumer_messages'][0]['content'] = json.dumps(value)
        result = m.analyze(p)['rows'][0]
        self.assertTrue(result['consumer_offer_alignment'])
        self.assertTrue(result['providers'][0]['prior_quote_consumed'])
        self.assertFalse(result['providers'][1]['prior_quote_consumed'])

    def test_current_override_errors_use_original_field_scorer(self):
        p = proof(override=True)
        raw = json.loads(p['rows'][0]['raw_answer'])
        raw['options'][0]['remaining'] = 999
        p['rows'][0]['raw_answer'] = json.dumps(raw)
        out = m.analyze(p)
        row = out['rows'][0]
        self.assertTrue(row['current_source_bound'])
        self.assertEqual(row['current_override_rule_errors'], ['A.remaining'])
        self.assertFalse(row['recorded_score_matches'])
        self.assertEqual(row['strict_score'], score_decision(p['rows'][0]['raw_answer'], p['fixtures'][0]['oracle']))
        self.assertEqual(out['metrics']['current_override_rule_errors']['denominator'], 1)

    def test_consumer_current_source_tamper_disables_attribution(self):
        p = proof(override=True)
        message = p['rows'][0]['consumer_messages'][0]
        value = json.loads(message['content'])
        value['current_source'] += ' fabricated rule'
        message['content'] = json.dumps(value)
        row = m.analyze(p)['rows'][0]
        self.assertFalse(row['current_source_bound'])
        self.assertIsNone(row['current_override_rule_errors'])

    def test_invalid_json_is_separate_from_valid_json_duplicate_entities(self):
        p = proof()
        p['rows'][0]['raw_answer'] = '{"action":"A","action":"B"}'
        out = m.analyze(p)
        self.assertEqual(out['rows'][0]['output_status'], 'INVALID_JSON')
        self.assertEqual(out['metrics']['invalid_json']['count'], 1)
        p = proof()
        value = json.loads(p['rows'][0]['raw_answer'])
        value['options'][1]['entity'] = 'A'
        p['rows'][0]['raw_answer'] = json.dumps(value)
        row = m.analyze(p)['rows'][0]
        self.assertEqual(row['output_status'], 'INVALID_DECISION_SCHEMA')
        self.assertEqual(row['strict_score']['utility'], 0)
        self.assertEqual(row['strict_score']['contradictions'], ['invalid:duplicate/invalid entity'])

    def test_incomplete_and_duplicate_rows_are_never_complete(self):
        p = proof()
        p['variant_spec'].append(['b1_only'])
        out = m.analyze(p)
        self.assertEqual(out['coverage']['expected_rows'], 2)
        self.assertEqual(out['coverage']['recorded_rows'], 1)
        self.assertFalse(out['coverage']['complete'])
        p = proof()
        p['rows'].append(copy.deepcopy(p['rows'][0]))
        out = m.analyze(p)
        self.assertFalse(out['coverage']['complete'])
        self.assertEqual(out['coverage']['duplicate_rows'], 1)

    def test_missing_native_metrics_stay_unavailable(self):
        p = proof()
        del p['rows'][0]['native_consumer_metrics']
        del p['rows'][0]['offers'][0]['native_metrics']
        out = m.analyze(p)
        self.assertEqual(out['metrics']['native_consumer_final'], {'count': 0, 'denominator': 0, 'unavailable_rows': 1, 'inapplicable_rows': 0})
        self.assertEqual(out['rows'][0]['providers'][0]['native_status'], 'UNAVAILABLE')

    def test_missing_consumer_messages_are_not_a_producer_pass(self):
        p = proof(quote_prior=True)
        del p['rows'][0]['consumer_messages']
        out = m.analyze(p)
        self.assertFalse(out['rows'][0]['current_source_bound'])
        self.assertIsNone(out['rows'][0]['providers'][0]['prior_quote_consumed'])
        self.assertEqual(out['metrics']['consumer_quote_transport_mismatch']['denominator'], 0)

    def test_unavailable_source_is_not_called_quote_transport_mismatch(self):
        p = proof(quote_prior=True)
        p['rows'][0]['source_evidence'] = p['rows'][0]['source_evidence'][:1]
        out = m.analyze(p)
        self.assertEqual(out['rows'][0]['providers'][0]['consumer_quote_transport'], 'UNAVAILABLE')
        self.assertEqual(out['metrics']['consumer_quote_transport_mismatch']['unavailable_rows'], 1)
        self.assertEqual(out['metrics']['consumer_quote_transport_mismatch']['count'], 0)

    def test_inapplicable_override_rows_are_separate_from_unavailable(self):
        out = m.analyze(proof())
        metric = out['metrics']['current_override_rule_errors']
        self.assertEqual(metric, {'count': 0, 'denominator': 0, 'unavailable_rows': 0, 'inapplicable_rows': 1})
        self.assertEqual(out['metrics']['sampled_native_peak_rss_bytes']['max_recorded'], None)


if __name__ == '__main__':
    unittest.main()
