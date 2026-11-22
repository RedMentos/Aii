"""R4 part 3: features, AUROC and counterfactual policy of scripts/r4_c3_uncertainty_wake.py (no model)."""
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import r4_c3_uncertainty_wake as W

class Features(unittest.TestCase):
    def test_features_from_token_logprobs(self):
        f=W.features([{'token':'The','logprob':-.1},{'token':' 42','logprob':-2.},{'token':'.','logprob':-.5}])
        self.assertEqual(f['min_logprob'],-2.);self.assertAlmostEqual(f['mean_logprob'],-2.6/3);self.assertEqual(f['digit_min_logprob'],-2.)
        self.assertAlmostEqual(f['share_below_half'],1/3);self.assertEqual(f['tokens'],3.);self.assertIsNone(W.features([]))
    def test_auroc_and_direction(self):
        self.assertEqual(W.auroc([3,2,1,0],[True,True,False,False]),1.);self.assertEqual(W.auroc([1,1],[True,False]),.5);self.assertIsNone(W.auroc([1],[True]))
        row={'features':{'min_logprob':-3.,'share_below_half':.4}}
        self.assertEqual(W.uncertainty(row,'min_logprob'),3.);self.assertEqual(W.uncertainty(row,'share_below_half'),.4)

class Policy(unittest.TestCase):
    def test_policy_reads_recorded_arm_outcomes(self):
        r4={'rows':[{'arm':'c_native_only','fixture':'a','pass':False,'turn_s':5.},{'arm':'always_ab','fixture':'a','pass':True,'turn_s':50.},
                    {'arm':'c_native_only','fixture':'b','pass':True,'turn_s':5.},{'arm':'always_ab','fixture':'b','pass':False,'turn_s':50.}]}
        rows=[{'fixture':'a','features':{'min_logprob':-4.}},{'fixture':'b','features':{'min_logprob':-.1}}]
        self.assertEqual(W.policy(rows,r4,'min_logprob',1.),{'pass':2,'woke':1,'turn_s':27.5})
        self.assertEqual(W.policy(rows,r4,'min_logprob',math.inf)['pass'],1)

if __name__=='__main__':unittest.main()
