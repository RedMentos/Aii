"""WP-DS3 policy scoring on synthetic rows (no models)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ds3_metacog_policy as P  # noqa: E402

def row(p1,c1,p3=None,c3=None):
    t=lambda ok,c:{'pass':ok,'features':{'digit_min_logprob':__import__('math').log(c)}}
    return {'fixture':'x00','pass1':t(p1,c1),'pass3':None if p3 is None else t(p3,c3)}

class DS3Tests(unittest.TestCase):
    def test_final_uses_tool_answer_when_present(self):
        self.assertEqual(P.final(row(False,.9,True,.99))[0],'after_tool');self.assertEqual(P.final(row(True,.9))[0],'no_tool')
    def test_abstains_only_below_threshold_and_scores_zero(self):
        tables={'no_tool':[.1]*5+[.9]*5}
        self.assertEqual(P.decide(row(False,.3),tables,.5),('abstain',None));self.assertEqual(P.decide(row(True,.95),tables,.5),('answer',True))
        s=P.score([('abstain',None),('answer',True),('answer',False)]);self.assertEqual((s['utility'],s['abstain']),(0.,1))
    def test_uncalibrated_component_never_abstains(self):
        self.assertEqual(P.decide(row(False,.01,False,.01),{'no_tool':[0.]*10},.5)[0],'tool')
    def test_recipe_always_never_abstains(self):
        self.assertEqual(P.outcomes([row(False,.01)],'recipe_always'),[('answer',False)])
    def test_auroc_and_ece(self):
        self.assertEqual(P.auroc([3,2,1,0],[True,True,False,False]),1.);self.assertEqual(P.ece([(.9,1),(.9,1)]),.1)

if __name__=='__main__':unittest.main()
