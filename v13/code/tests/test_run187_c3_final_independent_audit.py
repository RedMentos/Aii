"""Run187 independent raw C3 final-score audit, synthetic-only tests."""
import importlib.util
import json
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[1] / 'scripts/run187_c3_final_independent_audit.py'
spec = importlib.util.spec_from_file_location('run187', SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def row():
    return {'text': 'The approved budget is 20000 euros.', 'key': '20000',
            'kind': 'budget', 'stale': None, 'question': 'Budget?'}


def source():
    raw = json.dumps({'summary': '20000 euros', 'quotes': ['The approved budget is 20000 euros.']})
    return {'binding': {'model_sha256': m.B2_SHA}, **{
        arm: [{'index': i, 'content': raw} for i in range(36)] for arm in m.ARMS}}


def native():
    answer = json.dumps({'answer': '20000 euros', 'evidence_quote': 'The approved budget is 20000 euros.', 'uncertainty': ''})
    n = {'schema': 'V13_RUN186_C3_FINAL_GIST_UTILITY_V1',
         'binding': {'source_sha256': m.SOURCE_SHA, 'b2_sha256': m.B2_SHA,
                     'c3_sha256': m.C3_SHA, 'server_sha256': m.SERVER_SHA,
                     'corpus_rows': 36, 'seed': 13, 'temperature': 0},
         'activation_authorized': False, 'step2_promoted': False, 'b3_promoted': False,
         'redmi_proven': False, 'v13_complete': False,
         'jepa_weight': 0, 'body_jepa_available': False}
    for arm in m.ARMS:
        n[arm] = [{'index': i, 'kind': 'budget', 'prompt_tokens': 100,
                   'source_quote_count': 1, 'content': answer, 'parsed': True,
                   'answer_hit': True, 'quote_valid': True, 'quote_support': True,
                   'supported_hit': True, 'stale_without_new': False} for i in range(36)]
    n['summary'] = {arm: {'answer_hits': 36, 'supported_hits': 36,
                          'invalid_quotes': 0, 'stale_without_new': 0,
                          'mean_prompt_tokens': 100.0} for arm in m.ARMS}
    n['paired'] = {'wins': 0, 'losses': 0}
    n['criteria'] = {'paired_supported_wins_gt_losses': False,
                     'invalid_quotes_not_more': True, 'prompt_tokens_within_10pct': True}
    n['diagnostic'] = 'C3_GIST_FINAL_NO_GAIN'
    return n


class Audit(unittest.TestCase):
    def test_valid_complete(self):
        result = m.audit(native(), source(), [row() for _ in range(36)])
        self.assertEqual(result['status'], 'RUN187_INDEPENDENT_C3_FINAL_AUDIT_PASS')
        self.assertFalse(result['activation_authorized'])

    def test_wrong_source_binding(self):
        n = native();n['binding']['source_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'binding'):
            m.audit(n, source(), [row() for _ in range(36)])

    def test_duplicate_index(self):
        n = native();n['gist'][0]['index'] = 1
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            m.audit(n, source(), [row() for _ in range(36)])

    def test_score_tamper(self):
        n = native();n['gist'][0]['supported_hit'] = False
        with self.assertRaisesRegex(ValueError, 'score mismatch'):
            m.audit(n, source(), [row() for _ in range(36)])

    def test_quote_not_forwarded(self):
        n = native();n['gist'][0]['source_quote_count'] = 0
        with self.assertRaisesRegex(ValueError, 'quote count'):
            m.audit(n, source(), [row() for _ in range(36)])

    def test_aggregate_tamper(self):
        n = native();n['summary']['gist']['supported_hits'] = 0
        with self.assertRaisesRegex(ValueError, 'aggregate'):
            m.audit(n, source(), [row() for _ in range(36)])

    def test_authority_tamper(self):
        n = native();n['activation_authorized'] = True
        with self.assertRaisesRegex(ValueError, 'authority'):
            m.audit(n, source(), [row() for _ in range(36)])

    def test_numeric_substring(self):
        x = m._recompute(row(), json.dumps({'answer': '120000 euros',
           'evidence_quote': 'The approved budget is 20000 euros.'}),
           ['The approved budget is 20000 euros.'])
        self.assertFalse(x['answer_hit'])

    def test_duplicate_json_refused(self):
        x = m._recompute(row(), '{"answer":"20000","answer":"120000","evidence_quote":"The approved budget is 20000 euros."}',
           ['The approved budget is 20000 euros.'])
        self.assertFalse(x['parsed'])


if __name__ == '__main__':
    unittest.main()
