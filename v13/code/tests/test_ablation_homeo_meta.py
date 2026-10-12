"""Thread L §99-style ablations for metaplasticity and homeostasis: drive the real pure functions, verdict rule."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ablation_homeo_meta as A
from v13 import homeostasis as H

class HomeoMeta(unittest.TestCase):
    def test_streams_are_identical_per_seed_and_arms_differ(self):
        self.assertEqual(A.meta_stream(13)[5]['y'],A.meta_stream(13)[5]['y'])
        s=A.homeo_stream(13);self.assertEqual({e['path'] for e in s if e['phase']=='skewed'}-set(A.PATHS),set())
        self.assertNotIn(A.REVIVED,{e['path'] for e in s if e['phase']=='skewed'})
        v=A.run_meta(A.meta_stream(13),'v13');p=A.run_meta(A.meta_stream(13),'fixed_permissive')
        self.assertEqual(p['mean_p'],1.);self.assertLess(v['mean_p'],1.)
    def test_home_knobs_restored_after_ablation(self):
        old=dict(H.HOME)
        with A._home(dominant_path_inhibition=0.):self.assertEqual(H.HOME['dominant_path_inhibition'],0.)
        self.assertEqual(H.HOME,old)
    def test_verdict_rule(self):
        per={s:{'v13':{'primary':1.},'a':{'primary':2.},'b':{'primary':.5}} for s in range(5)}
        self.assertEqual(A._verdict(per,('v13','a','b'))['verdict'],'PARTIAL')
        per={s:{'v13':{'primary':1.},'a':{'primary':2.}} for s in range(5)};self.assertEqual(A._verdict(per,('v13','a'))['verdict'],'SUPPORTED_SYNTHETIC')

if __name__=='__main__':unittest.main()

import ablation_corollary as C
class Corollary(unittest.TestCase):
    def test_attribution_uses_real_function_and_safety_stays_raw(self):
        st=C.attr_stream(13);acts,obs=st
        self.assertEqual({o['truth'] for o in obs},{'SELF','MIXED','EXTERNAL'})
        self.assertEqual(C.run_attr(st,'no_corollary')['primary'],round(1/3,5))
        a=C.att_stream(13,40);rows={x:C.run_att(a,x,seed=1) for x in C.ATT_ARMS}
        self.assertTrue(all(rows[x]['raw_signals']==rows['v13']['raw_signals'] for x in rows))
        old=C.S.ATTENUATION
        with C._att(1.):pass
        self.assertEqual(C.S.ATTENUATION,old)
