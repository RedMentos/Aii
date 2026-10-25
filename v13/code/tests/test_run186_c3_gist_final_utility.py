"""Run186 synthetic-only final C3 consumer regression tests."""
import importlib.util
import json
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[1] / 'scripts/run186_c3_gist_final_utility.py'
spec = importlib.util.spec_from_file_location('run186', SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def row():
    return {'text': 'The approved budget is 20000 euros. The original deadline was March 3. The deadline moved to April 17.',
            'question': 'What is the budget?', 'key': '20000', 'stale': None, 'kind': 'budget'}


def offer(summary='Budget 20000 euros', quotes=None):
    if quotes is None: quotes=['The approved budget is 20000 euros.']
    return json.dumps({'summary': summary, 'quotes': quotes})


def answer(ans='20000 euros', quote='The approved budget is 20000 euros.'):
    return json.dumps({'answer': ans, 'evidence_quote': quote, 'uncertainty': ''})


class C3GistFinal(unittest.TestCase):
    def test_exact_source_quote_forwarded(self):
        x = m.prompt(row(), offer())
        self.assertEqual(x['source_quote_count'], 1)
        self.assertEqual(x['exact_source_quotes'], ['The approved budget is 20000 euros.'])

    def test_fabricated_quote_filtered(self):
        x = m.prompt(row(), offer(quotes=['invented source 20000']))
        self.assertEqual(x['source_quote_count'], 0)

    def test_correct_final_source_supported(self):
        x = m.score(row(), answer(), ['The approved budget is 20000 euros.'])
        self.assertTrue(x['supported_hit'])

    def test_numeric_substring_not_hit(self):
        x = m.score(row(), answer('120000 euros'))
        self.assertFalse(x['answer_hit'])

    def test_unsupported_final_not_supported(self):
        x = m.score(row(), answer('20000 euros', 'fake'), ['The approved budget is 20000 euros.'])
        self.assertFalse(x['supported_hit'])

    def test_unforwarded_quote_not_supported(self):
        x = m.score(row(), answer(), [])
        self.assertTrue(x['quote_valid'])
        self.assertFalse(x['supported_hit'])

    def test_duplicate_json_keys_refused(self):
        raw = '{"answer":"20000 euros","answer":"120000 euros","evidence_quote":"The approved budget is 20000 euros.","uncertainty":""}'
        self.assertFalse(m.score(row(), raw, ['The approved budget is 20000 euros.'])['parsed'])

    def test_malformed_json_not_supported(self):
        self.assertFalse(m.score(row(), '{broken')['parsed'])

    def test_report_binding(self):
        rr = {'kind': 'V13_G1B_GIST_UTILITY', 'binding': {'model_sha256': m.B2_SHA},
              'claim_limit': 'Linux not Redmi; B2 offer only'}
        for arm in m.ARMS:
            rr[arm] = [{'index': i, 'kind': 'budget', 'content': offer()} for i in range(36)]
        self.assertTrue(m.validate_b2_report(rr, [row() for _ in range(36)]))
        rr['gist'][0]['index'] = 1
        with self.assertRaisesRegex(ValueError, 'duplicate/missing'):
            m.validate_b2_report(rr, [row() for _ in range(36)])

    def test_paired_summary_and_gates(self):
        rr = {}
        for arm in m.ARMS:
            rr[arm] = [{'index': i, 'prompt_tokens': 100, 'answer_hit': arm=='gist',
                        'supported_hit': arm=='gist', 'quote_valid': arm=='gist',
                        'stale_without_new': False} for i in range(36)]
        x = m.summarize(rr)
        self.assertEqual(x['paired'], {'wins': 36, 'losses': 0})
        self.assertEqual(x['diagnostic'], 'C3_GIST_FINAL_UTILITY_CANDIDATE')

    def test_c3_model_pin(self):
        self.assertEqual(len(m.C3_SHA), 64)
        self.assertNotEqual(m.C3_SHA, m.B2_SHA)


if __name__ == '__main__':
    unittest.main()
