"""WP-KAL2: token-logprob offer uncertainty and result-stating offer prompt."""
import unittest
from v13 import focal
from v13.cognition import offer_instructions,OFFER_STYLE

def pairs(tokens,lps):return list(zip(tokens,lps))

class TokenConfidence(unittest.TestCase):
    def test_summary_span_only(self):
        toks=['{','"summary','":"','The',' result',' is',' 108','","','quotes','":[]}']
        lps=[-9.,-.1,-.1,-.05,-.05,-.05,-2.,-.1,-.1,-.1]
        tc=focal.token_confidence(pairs(toks,lps))
        self.assertEqual(tc['field_tokens'],4)
        self.assertAlmostEqual(tc['field_min_prob'],round(2.718281828**-2.,4),places=3)
        self.assertLess(tc['mean_prob'],tc['field_mean_prob'])  # forced JSON syntax drags the all-token mean down
    def test_missing_field_and_bad_values(self):
        tc=focal.token_confidence([('{',-.1),('x',float('nan'))])
        self.assertIsNone(tc['field_min_prob']);self.assertEqual(tc['n'],1)

class OfferUncertainty(unittest.TestCase):
    def offer(self,role,conf,reentry=False,refs=1):
        return {'role':role,'offer':{'needs_reentry':reentry,'uncertainty':'low'},'evidence_refs':[{}]*refs,
                'native_metrics':{'token_confidence':{'field_min_prob':conf}}}
    def test_pivot_maps_to_trigger_per_role(self):
        trig=focal.BOOT['uncertainty_trigger']
        for role,piv in focal.TOKEN_UNC['pivot'].items():
            self.assertAlmostEqual(focal.offer_uncertainty(self.offer(role,1-piv)),trig,places=3)
        self.assertGreater(focal.offer_uncertainty(self.offer('B1_DETAIL',.1)),trig)
        self.assertLess(focal.offer_uncertainty(self.offer('B1_DETAIL',.99)),trig)
    def test_monotone_and_reentry_floor(self):
        u=[focal.offer_uncertainty(self.offer('B2_GIST',c)) for c in (.99,.8,.5,.2,.01)]
        self.assertEqual(u,sorted(u))
        self.assertGreaterEqual(focal.offer_uncertainty(self.offer('B1_DETAIL',.99,reentry=True)),.6)
        self.assertGreater(focal.offer_uncertainty(self.offer('B1_DETAIL',.9,refs=0)),focal.offer_uncertainty(self.offer('B1_DETAIL',.9)))
    def test_legacy_fallback_without_logprobs(self):
        p={'offer':{'needs_reentry':False,'uncertainty':'unclear date'},'evidence_refs':[{}]}
        self.assertEqual(focal.offer_uncertainty(p),.4)

class OfferPrompt(unittest.TestCase):
    def test_default_asks_for_result(self):
        self.assertEqual(OFFER_STYLE,'solve')
        self.assertIn('states the exact result',offer_instructions('B1_DETAIL'))
        self.assertIn('gist analyst',offer_instructions('B2_GIST'))
        self.assertIn('NOT a final user answer',offer_instructions('B1_DETAIL','hypothesis'))

if __name__=='__main__':unittest.main()
