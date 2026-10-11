"""G9/§24.21 developmental age envelope with simulated evidence; no model quality claim."""
import json
from pathlib import Path
import tempfile
import unittest
from v13.config import initialize
from v13.store import Store
from v13 import age

GOOD={'experience':10000,'competence':.95,'stability':.95,'retention':.98,'calibration':.9,'memory_health':.97,'safe_self_control':.999,'regression_pass':True}

def good(**kw):return GOOD|kw

class AgeChecks(unittest.TestCase):
    def setUp(self):
        self.td=tempfile.TemporaryDirectory();self.home=Path(self.td.name);self.cfg=initialize(self.home);self.store=Store(self.home)
    def tearDown(self):
        self.store.close();self.td.cleanup()
    def ctl(self,cap=5,ceiling=5):
        self.cfg['user_stage_cap']=cap;return age.AgeControl(self.store,self.cfg,build_ceiling=ceiling)

    def test_default_build_stays_age0_but_records_proposal(self):
        a=age.AgeControl(self.store,self.cfg|{'user_stage_cap':5})
        for _ in range(5):out=a.record('system',good())
        self.assertEqual(a.system_stage(),0);self.assertEqual(out['proposal']['blocked_by'],'build_ceiling')
        self.assertFalse(a.allowed('short_dream'));self.assertTrue(a.allowed('direct_route'))

    def test_promotion_needs_several_distinct_passes(self):
        a=self.ctl()
        a.record('system',good());a.record('system',good());self.assertEqual(a.system_stage(),0)
        a.record('system',good(competence=.1))  # one bad result resets the streak
        a.record('system',good());a.record('system',good());self.assertEqual(a.system_stage(),0)
        self.assertEqual(a.record('system',good())['change']['kind'],'PROMOTE');self.assertEqual(a.system_stage(),1)
        with self.assertRaises(ValueError):a.record('system',good(),evidence_id=a.state()[0]['system']['last_evidence'])

    def test_user_cap_is_binding_and_not_self_overridable(self):
        a=self.ctl(cap=1)
        for _ in range(12):out=a.record('system',good())
        self.assertEqual(a.system_stage(),1);self.assertEqual(out['proposal'],{**out['proposal'],'to':2,'blocked_by':'user_stage_cap'})
        self.assertFalse(a.allowed('deliberation_modes'));self.assertFalse(a.allowed('exceed_user_stage_cap'))
        self.cfg['user_stage_cap']=0;self.assertEqual(a.system_stage(),0);self.assertEqual(len(a.apply_cap()),1)
        self.assertEqual(a.state()[0]['system']['stage'],0)

    def test_hysteresis_band_and_demotion(self):
        a=self.ctl()
        for _ in range(3):a.record('system',good())
        self.assertEqual(a.system_stage(),1)
        # below the promotion gate but inside the maintenance band: no demotion
        for _ in range(4):a.record('system',good(competence=.57,experience=60))
        self.assertEqual(a.system_stage(),1)
        before=a.budgets()
        a.record('system',good(competence=.3));self.assertEqual(a.system_stage(),1)
        self.assertEqual(a.record('system',good(competence=.3))['change']['kind'],'DEMOTE');self.assertEqual(a.system_stage(),0)
        after=a.budgets();self.assertLessEqual(after['own_loops'],before['own_loops']);self.assertLessEqual(after['dream_seconds'],before['dream_seconds'])

    def test_severe_regression_demotes_immediately(self):
        a=self.ctl()
        for _ in range(6):a.record('system',good())
        self.assertEqual(a.system_stage(),2)
        a.record('system',good(retention=.5,regression_pass=False));self.assertEqual(a.system_stage(),1)

    def test_capability_stage_scaffolds_even_if_system_is_mature(self):
        a=self.ctl()
        for _ in range(12):a.record('system',good())
        self.assertEqual(a.system_stage(),4)
        self.assertTrue(a.allowed('self_initiative'));self.assertFalse(a.allowed('self_initiative','vision'))
        self.assertEqual(a.ceiling('vision'),0)
        for _ in range(6):a.record('language',good())
        self.assertEqual(a.ceiling('language'),2);self.assertTrue(a.allowed('deliberation_modes','language'));self.assertFalse(a.allowed('long_loops','language'))

    def test_rights_are_masked_by_rules_permissions_resources_and_structural_lock(self):
        a=self.ctl()
        for _ in range(15):a.record('system',good())
        self.assertEqual(a.system_stage(),5)
        self.assertFalse(a.allowed('structural_modification'));a.lock_structural(False);self.assertTrue(a.allowed('structural_modification'))
        self.assertFalse(a.allowed('edit_hard_rules'))
        self.assertFalse(a.allowed('long_loops',hard_rule_block=True));self.assertFalse(a.allowed('long_loops',user_permissions={'direct_route'}))
        self.assertFalse(a.allowed('short_dream',resource_mode='RED'));self.assertTrue(a.allowed('short_dream',resource_mode='GREEN'))
        self.assertEqual(a.budgets(resource_mode='RED')['dream_seconds'],0)

    def test_continuous_maturity_changes_budgets_smoothly_within_stage(self):
        a=self.ctl(cap=0)
        values=[]
        for _ in range(8):a.record('system',good());values.append(a.budgets()['context_edit_tokens'])
        self.assertEqual(a.system_stage(),0)
        self.assertEqual(values,sorted(values));self.assertTrue(all(0<=v<=32 for v in values))
        self.assertTrue(all(b-x<=8 for x,b in zip(values,values[1:])))

    def test_gist_resolution_grows_with_maturity_but_refines_on_novelty(self):
        a=self.ctl()
        self.assertEqual(a.gist_resolution()['tokens_per_group'],8);self.assertEqual(a.gist_resolution()['slots'],12)
        for _ in range(9):a.record('language',good())
        for _ in range(9):a.record('system',good())
        mature=a.gist_resolution()['tokens_per_group'];self.assertGreater(mature,8)
        self.assertLess(a.gist_resolution(novelty=1.)['tokens_per_group'],mature)
        self.assertEqual(a.gist_resolution(literal=True)['tokens_per_group'],age.GIST_FINE)

    def test_reopenable_plasticity(self):
        a=self.ctl()
        for _ in range(12):a.record('language',good())
        mature=a.plasticity('language');self.assertLess(mature,.6)
        self.assertGreaterEqual(a.plasticity('language',novel_domain=True),.8)
        self.assertGreater(a.plasticity('language',repeated_errors=2),mature)
        a.open_window('haptics');self.assertEqual(a.ceiling('haptics'),0);self.assertEqual(a.plasticity('haptics',new_modality=True),1.)

    def test_user_freeze_and_lower(self):
        a=self.ctl()
        a.freeze(True)
        for _ in range(4):out=a.record('system',good())
        self.assertEqual(a.system_stage(),0);self.assertEqual(out['proposal']['blocked_by'],'frozen')
        a.freeze(False);a.record('system',good());self.assertEqual(a.system_stage(),1)
        with self.assertRaises(ValueError):a.lower('system',3)
        a.lower('system',0);self.assertEqual(a.system_stage(),0)

    def test_restart_persists_state(self):
        a=self.ctl()
        for _ in range(3):a.record('system',good())
        a.record('memory_skill',good());self.store.close()
        self.store=Store(self.home);b=age.AgeControl(self.store,self.cfg,build_ceiling=5)
        self.assertEqual(b.system_stage(),1);self.assertEqual(b.view()['capabilities']['memory_skill']['pass_streak'],1)
        self.assertEqual(b.state()[0]['history'][-1]['kind'],'PROMOTE')
        self.assertEqual(self.store.rows("SELECT kind FROM telemetry WHERE kind='age_transition'")[0]['kind'],'age_transition')

class AgeOperatorChecks(unittest.TestCase):
    def test_operator_age_shows_real_state(self):
        from v13.runtime import Runtime
        from v13.operator import Operator
        with tempfile.TemporaryDirectory() as td:
            r=Runtime(Path(td))
            try:
                op=Operator(r);v=json.loads(op.run(':age'))
                self.assertEqual(v['system_stage'],0);self.assertEqual(v['build_ceiling'],0);self.assertIn('language',v['capabilities'])
                op.run(':stage cap 3');self.assertEqual(json.loads(op.run(':age'))['user_stage_cap'],3)
                self.assertTrue(json.loads(op.run(':age freeze on'))['frozen'])
                self.assertIn('language',json.loads(op.run(':capability')))
                self.assertEqual(json.loads(op.run(':capability language stage 0'))['kind'],'USER_LOWER')
                with self.assertRaises(ValueError):op.run(':capability language stage 2')
                self.assertEqual(json.loads(op.run(':status'))['age'],0);self.assertEqual(r.cfg['system_stage'],0)
            finally:r.close()

if __name__=='__main__':unittest.main()
