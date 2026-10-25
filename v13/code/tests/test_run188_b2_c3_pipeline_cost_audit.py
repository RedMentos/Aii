"""Run188 synthetic total-cost audit tests; no native model calls."""
import importlib.util
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[1] / 'scripts/run188_b2_c3_pipeline_cost_audit.py'
spec = importlib.util.spec_from_file_location('run188', SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def corpus():
    return [{'kind': 'budget'} for _ in range(36)]


def reports(gist_b2=200, gist_c3=100, gist_hits=20, fixed_hits=10):
    b2={'kind': 'V13_G1B_GIST_UTILITY'}
    c3={'schema': 'V13_RUN186_C3_FINAL_GIST_UTILITY_V1',
        'activation_authorized': False, 'step2_promoted': False,
        'b3_promoted': False, 'redmi_proven': False, 'v13_complete': False}
    for arm in m.ARMS:
        b2_tokens = gist_b2 if arm == 'gist' else 100
        c3_tokens = gist_c3 if arm == 'gist' else 100
        hits = gist_hits if arm == 'gist' else fixed_hits
        b2[arm]=[{'index': i, 'kind': 'budget', 'prompt_tokens': b2_tokens, 'seconds': b2_tokens/100} for i in range(36)]
        c3[arm]=[{'index': i, 'kind': 'budget', 'prompt_tokens': c3_tokens, 'seconds': c3_tokens/100,
                  'supported_hit': i < hits, 'quote_valid': True} for i in range(36)]
    return b2,c3


class PipelineCost(unittest.TestCase):
    def test_cost_blocks_candidate_despite_hits(self):
        b,c=reports()
        out=m.audit(b,c,corpus())
        self.assertEqual(out['paired'], {'wins': 10, 'losses': 0})
        self.assertEqual(out['diagnostic'], 'PIPELINE_TOTAL_COST_NO_GAIN')
        self.assertFalse(out['criteria']['total_prompt_tokens_within_10pct'])
        self.assertFalse(out['activation_authorized'])

    def test_equal_cost_allows_candidate(self):
        b,c=reports(gist_b2=100)
        out=m.audit(b,c,corpus())
        self.assertEqual(out['diagnostic'], 'PIPELINE_TOTAL_COST_CANDIDATE')

    def test_duplicate_index_refused(self):
        b,c=reports();c['gist'][0]['index']=1
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            m.audit(b,c,corpus())

    def test_missing_arm_refused(self):
        b,c=reports();b['gist'].pop()
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            m.audit(b,c,corpus())

    def test_invalid_tokens_refused(self):
        b,c=reports();b['gist'][0]['prompt_tokens']=0
        with self.assertRaisesRegex(ValueError, 'tokens'):
            m.audit(b,c,corpus())

    def test_authority_refused(self):
        b,c=reports();c['step2_promoted']=True
        with self.assertRaisesRegex(ValueError, 'authority'):
            m.audit(b,c,corpus())

    def test_seconds_rejected(self):
        b,c=reports();c['gist'][0]['seconds']=-1
        with self.assertRaisesRegex(ValueError, 'seconds'):
            m.audit(b,c,corpus())


if __name__ == '__main__':
    unittest.main()
