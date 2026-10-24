import random
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import age_cross_source_signal as A

def votes(labels,quality=1.,sources=('s1','s2')):
    return [{'case_id':case,'source_id':source,'label':label,'source_quality':quality}
            for case,label in labels.items() for source in sources]

class AgeSourceTests(unittest.TestCase):
    def setUp(self):self.base={f'c{i}':i%2 for i in range(5)}
    def test_coherent_shift_candidate(self):
        new={k:1-v for k,v in self.base.items()}
        self.assertEqual(A.assess(votes(self.base),votes(new))['status'],'SHIFT_CANDIDATE')
    def test_one_bad_source_is_noise_not_shift(self):
        rows=votes(self.base)
        rows[0]['label']=1-rows[0]['label']
        self.assertEqual(A.assess(votes(self.base),rows)['status'],'NOISE_SUSPECTED')
    def test_single_source_cannot_claim_shift(self):
        new={k:1-v for k,v in self.base.items()}
        self.assertEqual(A.assess(votes(self.base,sources=('s1',)),votes(new,sources=('s1',)))['status'],'INSUFFICIENT_EVIDENCE')
    def test_low_quality_sources_ignored(self):
        new={k:1-v for k,v in self.base.items()}
        self.assertEqual(A.assess(votes(self.base),votes(new,quality=.1))['status'],'INSUFFICIENT_EVIDENCE')
    def test_duplicate_source_does_not_inflate_diversity(self):
        new={k:1-v for k,v in self.base.items()}
        rows=votes(new,sources=('s1',))*3
        self.assertEqual(A.assess(votes(self.base),rows)['status'],'INSUFFICIENT_EVIDENCE')
    def test_conflicting_duplicate_source_rejected(self):
        rows=votes(self.base);rows.append({**rows[0],'label':1-rows[0]['label']})
        with self.assertRaises(ValueError):A.assess(votes(self.base),rows)
    def test_invalid_quality_or_label_rejected(self):
        for q in (float('nan'),-1,2,True):
            rows=votes(self.base);rows[0]['source_quality']=q
            with self.assertRaises(ValueError):A.assess(votes(self.base),rows)
        rows=votes(self.base);rows[0]['label']=.5
        with self.assertRaises(ValueError):A.assess(votes(self.base),rows)
    def test_no_authority_or_gate_promotion(self):
        r=A.assess(votes(self.base),votes(self.base))
        self.assertEqual(r['authority'],'SHADOW_NO_AGE_ACTION')
        self.assertFalse(r['canonical_gate_pass'])
        self.assertNotIn('plasticity',r)

if __name__=='__main__':unittest.main()
