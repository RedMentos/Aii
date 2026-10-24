import random
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import age_cross_source_signal_v2 as V

def votes(labels):
    return [{'case_id':case,'source_id':f's{j}','label':label,'source_quality':1.}
            for case,label in labels.items() for j in range(4)]

class SourceV2(unittest.TestCase):
    def setUp(self):self.base={f'c{i}':i%2 for i in range(5)}
    def test_majority_accepts_one_noisy_source(self):
        new={k:1-v for k,v in self.base.items()}
        rows=votes(new)
        for i in range(0,len(rows),4):rows[i]['label']=1-rows[i]['label']
        self.assertEqual(V.assess(votes(self.base),rows)['status'],'SHIFT_CANDIDATE')
    def test_two_two_tie_is_disputed(self):
        rows=votes(self.base)
        for i in range(0,len(rows),4):
            rows[i]['label']=1-rows[i]['label'];rows[i+1]['label']=1-rows[i+1]['label']
        self.assertEqual(V.assess(votes(self.base),rows)['status'],'NOISE_SUSPECTED')
    def test_single_source_insufficient(self):
        rows=[r for r in votes(self.base) if r['source_id']=='s0']
        self.assertEqual(V.assess(rows,rows)['status'],'INSUFFICIENT_EVIDENCE')
    def test_duplicate_source_does_not_inflate(self):
        rows=[r for r in votes(self.base) if r['source_id']=='s0']*4
        self.assertEqual(V.assess(rows,rows)['status'],'INSUFFICIENT_EVIDENCE')
    def test_untrusted_quality_cannot_vote(self):
        rows=votes(self.base)
        for r in rows:r['source_quality']=.2
        self.assertEqual(V.assess(votes(self.base),rows)['status'],'INSUFFICIENT_EVIDENCE')
    def test_correlated_sources_can_spoof_shift_unverified(self):
        # All four claimed sources repeat one upstream wrong label: cannot
        # establish independence from IDs alone. This is a known limitation.
        new={k:1-v for k,v in self.base.items()}
        r=V.assess(votes(self.base),votes(new))
        self.assertEqual(r['status'],'SHIFT_CANDIDATE')
        self.assertFalse(r['source_independence_verified'])

    def test_no_age_authority(self):
        r=V.assess(votes(self.base),votes(self.base))
        self.assertEqual(r['authority'],'SHADOW_NO_AGE_ACTION')
        self.assertFalse(r['canonical_gate_pass'])

if __name__=='__main__':unittest.main()
