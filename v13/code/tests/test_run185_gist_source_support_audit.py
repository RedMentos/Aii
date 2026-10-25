"""Run185 independent B2 offer support counterexamples; synthetic only."""
import importlib.util
import json
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[1] / 'scripts/run185_gist_source_support_audit.py'
spec = importlib.util.spec_from_file_location('run185', SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def row(key='20000', kind='budget'):
    return {'text': 'The approved budget is 20000 euros. Old estimate was 12000 euros.',
            'key': key, 'stale': None, 'kind': kind}


def content(summary, quotes):
    return json.dumps({'summary': summary, 'quotes': quotes})


def cohort():
    return [row() for _ in range(36)]


def report(raw=None):
    raw = raw or content('20000 euros', ['The approved budget is 20000 euros.'])
    arms = {arm: [{'index': i, 'kind': 'budget', 'prompt_tokens': 100,
                   'content': raw, 'hit': True, 'quotes_valid': True} for i in range(36)] for arm in m.ARMS}
    return {'kind': 'V13_G1B_GIST_UTILITY', 'binding': {'model_sha256': m.MODEL_SHA},
            'claim_limit': 'Linux, not Redmi; B2 offer only', 'decision': {'verdict': 'GIST_HELPS_CANDIDATE'}, **arms}


class SourceSupport(unittest.TestCase):
    def test_budget_substring_not_exact(self):
        x = m.classify(row(), content('120000 euros', ['The approved budget is 20000 euros.']))
        self.assertFalse(x['summary_hit'])
        self.assertFalse(x['source_supported_hit'])

    def test_empty_quotes_not_valid(self):
        x = m.classify(row(), content('20000 euros', []))
        self.assertTrue(x['summary_hit'])
        self.assertFalse(x['quotes_valid_nonempty'])
        self.assertFalse(x['source_supported_hit'])

    def test_correct_quote_support(self):
        x = m.classify(row(), content('20000 euros', ['The approved budget is 20000 euros.']))
        self.assertTrue(x['source_supported_hit'])

    def test_fabricated_quote_refused(self):
        x = m.classify(row(), content('20000 euros', ['budget 20000']))
        self.assertFalse(x['source_supported_hit'])

    def test_duplicate_json_key_refused(self):
        raw = '{"summary":"20000 euros","summary":"120000 euros","quotes":[]}'
        self.assertFalse(m.classify(row(), raw)['parsed'])

    def test_invalid_json_refused(self):
        self.assertFalse(m.classify(row(), '{oops')['parsed'])
        self.assertFalse(m.classify(row(), '[]')['parsed'])

    def test_stale_even_when_new_mentioned(self):
        r = {'text': 'The deadline moved from March 3 to April 17.', 'key': 'April 17',
             'stale': 'March 3', 'kind': 'deadline'}
        x = m.classify(r, content('New April 17, old March 3', ['The deadline moved from March 3 to April 17.']))
        self.assertTrue(x['source_supported_hit'])
        self.assertTrue(x['mentions_stale'])

    def test_complete_report_no_authority(self):
        out = m.audit(report(), cohort())
        self.assertEqual(out['summary']['gist']['source_supported_hits'], 36)
        self.assertEqual(out['paired'], {'wins': 0, 'losses': 0})
        self.assertFalse(out['activation_authorized'])
        self.assertFalse(out['step2_promoted'])
        self.assertEqual(out['diagnostic_only'], 'NO_SUPPORTED_GIST_GAIN')

    def test_reject_duplicate_and_incomplete(self):
        r = report();r['gist'][0]['index'] = 1
        with self.assertRaisesRegex(ValueError, 'duplicated'):
            m.audit(r, cohort())
        r = report();r['gist'].pop()
        with self.assertRaisesRegex(ValueError, 'partial'):
            m.audit(r, cohort())

    def test_reject_wrong_model(self):
        r = report();r['binding']['model_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'model SHA'):
            m.audit(r, cohort())

    def test_posthoc_diagnostic_not_original_verdict(self):
        r = report(content('120000 euros', []))
        out = m.audit(r, cohort())
        self.assertEqual(out['original_preregistered_verdict'], 'GIST_HELPS_CANDIDATE')
        self.assertEqual(out['summary']['gist']['source_supported_hits'], 0)
        self.assertEqual(out['diagnostic_only'], 'NO_SUPPORTED_GIST_GAIN')


if __name__ == '__main__':
    unittest.main()
