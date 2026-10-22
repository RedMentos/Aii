"""WP-DS2 lab sandbox: combined policy and generalizing learners run end to end. No models needed."""
import unittest
from v13 import sandbox as S
from v13 import sandbox_ds2 as D

class SandboxDS2Tests(unittest.TestCase):
    def test_item_tables_are_distributions(self):
        for it in D.TRAIN_ITEMS+D.HOLDOUT:
            for a in D.ACTIONS:self.assertAlmostEqual(sum(D.true2(it,a)),1.,9,(it,a))
    def test_adjective_overrides_part_of_the_noun(self):
        p=D.true2(('zerbrechlich','apfel'),'push');self.assertAlmostEqual(p[S.OUTCOMES.index('BROKE')],.5)
        self.assertEqual(D.true2(('leuchtend','glas'),'eat'),D.true2((None,'glas'),'eat'))
    def test_wachsapfel_looks_like_apfel_but_is_not_edible(self):
        self.assertEqual(D.true2((None,'wachsapfel'),'eat')[S.OUTCOMES.index('EATEN')],0.)
        self.assertTrue(set(D.VIS['apfel'])<set(D.VIS['wachsapfel']))
    def test_dsi_policies_unchanged(self):
        """lp/efe through AgentA give exactly the DS1 result."""
        for p in('lp','efe'):self.assertEqual(D.run_a(p,4,steps=300,new_kind_at=150),S.run(p,4,steps=300,new_kind_at=150))
    def test_combined_policies_run_and_are_deterministic(self):
        for p in('lpgoal','lpgoal_noboost'):
            a=D.run_a(p,5,steps=300,new_kind_at=150);self.assertEqual(a,D.run_a(p,5,steps=300,new_kind_at=150));self.assertGreater(a['interactions'],0)
    def test_feat_model_generalizes_to_unseen_lookalike(self):
        r=D.run_b(2,steps=700,holdout_at=500)
        self.assertLess(r['first_kl']['birne']['feat'],r['first_kl']['birne']['flat'])
    def test_feat_fit_lowers_loss(self):
        m=D.FeatModel();data={((None,'apfel'),'eat'):[0,0,9,0,0,0,0]}
        before=m.predict((None,'apfel'),'eat')[2];m.fit(data);self.assertGreater(m.predict((None,'apfel'),'eat')[2],before)

if __name__=='__main__':unittest.main()
