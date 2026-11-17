"""Synthetic negative tests for the phone receipt metadata gate; not real Redmi proof."""
import unittest
from scripts.qa_phone_20turn_gate import evaluate

def fixture():
    kinds = ['greeting', 'simple_math', 'nontrivial', 'ambiguity', 'memory_recall', 'body_cooperation']
    turns = []
    for i in range(20):
        turns.append({'correlation_id': f'turn-{i}', 'class': kinds[i % 6],
                      'status': 'FINAL', 'visible_answer': True, 'correct': True,
                      'total_ms': 2000 + i, 'first_token_ms': 500 + i,
                      'offers': {role: {'source_bound': True, 'delivered': True, 'consumed_by_c4_c3': True}
                                 for role in ('B1', 'B2')}})
    return {'evidence_origin': 'owner_consented_redmi_receipt', 'installed_sha': 'a' * 40, 'turns': turns}

class ReceiptGateTests(unittest.TestCase):
    def test_metadata_shape_is_not_attestation(self):
        self.assertEqual(evaluate(fixture())['status'], 'METADATA_PASS_UNATTESTED')
    def test_missing_consent_label(self):
        d = fixture(); d['evidence_origin'] = 'synthetic'
        self.assertEqual(evaluate(d)['status'], 'BLOCKED')
    def test_incorrect_answer(self):
        d = fixture(); d['turns'][1]['correct'] = False
        self.assertEqual(evaluate(d)['status'], 'BLOCKED')
    def test_unconsumed_body(self):
        d = fixture(); d['turns'][5]['offers']['B2']['consumed_by_c4_c3'] = False
        self.assertEqual(evaluate(d)['status'], 'BLOCKED')
    def test_duplicate_and_nan(self):
        d = fixture(); d['turns'][1]['correlation_id'] = 'turn-0'; d['turns'][2]['total_ms'] = float('nan')
        self.assertEqual(evaluate(d)['status'], 'BLOCKED')
    def test_impossible_first_token_after_final(self):
        d = fixture(); d['turns'][3]['first_token_ms'] = 3000
        result = evaluate(d)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertTrue(any('first token later' in failure for failure in result['failures']))
    def test_unknown_task_class_rejected(self):
        d = fixture(); d['turns'][4]['class'] = 'device_control_unverified'
        result = evaluate(d)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertTrue(any('unknown task class' in failure for failure in result['failures']))
    def test_boundary_equal_latency_allowed(self):
        d = fixture(); d['turns'][0]['first_token_ms'] = d['turns'][0]['total_ms']
        self.assertEqual(evaluate(d)['status'], 'METADATA_PASS_UNATTESTED')
    def test_insufficient_turns(self):
        d = fixture(); d['turns'] = d['turns'][:19]
        self.assertEqual(evaluate(d)['status'], 'BLOCKED')

if __name__ == '__main__':
    unittest.main()
