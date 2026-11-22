"""WP-S4 rest: pair rule, disjoint folds and the preregistered decision rule of scripts/sigreg_real_taps.py."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import sigreg_real_taps as S

def row(ok=True,noncollapse=True,ratio=.9,top1=.1):
    return {'commit_eligible':ok,'noncollapse_pass':noncollapse,'predictive_ablation_pass':ok,'retention_pass':True,'ratio_copy':ratio,
            'retrieval':{'prediction_top1':top1,'copy_top1':.05},'after':{'target_std_mean':.5,'context_isotropy':.3}}

def results(healthy,shrunk):
    out={}
    for budget in S.BUDGETS:
        for regime in S.REGIMES:
            for f in range(S.FOLDS):
                for mode in S.MODES:
                    out[f'{budget}/{regime}/f{f}/healthy/{mode}']=healthy[mode]
                    out[f'{budget}/{regime}/f{f}/shrunk/{mode}']=shrunk[mode]
    return out

class PairsAndFolds(unittest.TestCase):
    def test_pairs_follow_learning_rule_and_mask(self):
        H=np.arange(2*12*2048,dtype=np.float32).reshape(2,12,2048);M=np.zeros((2,12),np.float32);M[0,:12]=1;M[1,:9]=1
        x,y,g=S.pairs(H,M,[0,1])
        # note 0 (12 tokens): i=3,6,9 ; note 1 (9 tokens): i=3,6
        self.assertEqual(g,['note-0']*3+['note-1']*2)
        np.testing.assert_array_equal(x[0],H[0,3]);np.testing.assert_array_equal(y[0],H[0,5]);np.testing.assert_array_equal(y[-1],H[1,8])
    def test_folds_are_disjoint_and_exclude_dev_notes(self):
        f=S.folds();notes=[n for regime in f.values() for fold in regime for n in fold]
        self.assertEqual(len(notes),len(set(notes)));self.assertEqual(len(notes),S.FOLDS*sum(S.REGIMES.values()))
        self.assertTrue(all(n>=S.DEV_NOTES.stop for n in notes));self.assertEqual(f,S.folds())
    def test_arm_count(self):self.assertEqual(len(S.arms()),2*2*5*2*3)

class Decision(unittest.TestCase):
    def test_sigreg_wins_only_when_every_clause_holds(self):
        s=S.summarize(results({'ema':row(ratio=.9),'sigreg':row(ratio=.8,top1=.12),'both':row(ratio=.85)},
                              {'ema':row(noncollapse=False),'sigreg':row(),'both':row()}))
        self.assertEqual(s['per_budget']['runtime'],'BEATS_EMA:sigreg');self.assertEqual(s['verdict'],'CHANGE_DEFAULT_TO_SIGREG')
    def test_no_shrunk_advantage_keeps_ema(self):
        s=S.summarize(results({'ema':row(),'sigreg':row(ratio=.5,top1=.3),'both':row()},{'ema':row(),'sigreg':row(),'both':row()}))
        self.assertEqual(s['verdict'],'DEFAULT_STAYS_EMA')
    def test_worse_retrieval_keeps_ema(self):
        s=S.summarize(results({'ema':row(top1=.2),'sigreg':row(ratio=.5,top1=.1),'both':row(top1=.1)},
                              {'ema':row(noncollapse=False),'sigreg':row(),'both':row()}))
        self.assertEqual(s['per_budget']['runtime'],'EMA_NOT_BEATEN')
    def test_incomplete_is_never_a_verdict(self):
        r=results({m:row() for m in S.MODES},{m:row() for m in S.MODES});r.pop('runtime/R16/f0/healthy/ema')
        self.assertEqual(S.summarize(r)['verdict'],'INCOMPLETE')

if __name__=='__main__':unittest.main()
