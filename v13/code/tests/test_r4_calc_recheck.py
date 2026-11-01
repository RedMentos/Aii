"""R4 part 4: counterfactual policy logic of scripts/r4_calc_recheck.py (no model)."""
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import r4_calc_recheck as C

def row(fid,p1,unc,p3,expr_s=1.):
    return {'fixture':fid,'pass1':{'pass':p1,'turn_s':4.,'features':{'digit_min_logprob':-unc}},
            'expression':{'s':expr_s,'value':None if p3 is None else 1},'pass3':None if p3 is None else {'pass':p3,'turn_s':5.}}

class Policies(unittest.TestCase):
    def test_policies(self):
        rows=[row('summary00',False,2.,True),row('summary01',True,.1,False),row('compare00',False,2.,None)]
        self.assertEqual(C.score(rows,'c3_alone')['pass'],1)
        self.assertEqual(C.score(rows,'calc_always'),{'pass':1,'calc_turns':2,'mean_turn_s':round((10+10+5)/3,2),'by_kind':{'summary':1,'compare':0}})
        u=C.score(rows,'calc_uncertain',1.);self.assertEqual((u['pass'],u['calc_turns']),(2,1))
        self.assertEqual(C.score(rows,'calc_uncertain',math.inf)['pass'],1)
    def test_missing_features_count_as_uncertain(self):
        r=row('notes00',True,0.,False);r['pass1']['features']=None
        self.assertEqual(C.outcome(r,'calc_uncertain',5.),(False,10.,True))  # no digit tokens -> maximally uncertain (frozen design)

if __name__=='__main__':unittest.main()
