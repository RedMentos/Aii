import math
import unittest
import numpy as np
from v13 import world_model as W
from tests.test_world_model_integration_run64 import Store


class WorldAlignFinite(unittest.TestCase):
    def test_huge_finite_latent_is_not_measured(self):
        s=Store()
        for i in range(24):s.add(i,chars=20+i,duration=.1+i*.01,output=10+i,route=W.ACTIONS[i%4],latent=[1e308,1e308])
        result=W.fit(s,rng_seed=42)
        self.assertEqual(result['status'],'FITTED')
        self.assertEqual(result['metrics']['state_align'],{'status':'UNAVAILABLE','reason':'NUMERIC_UNSTABLE_LATENT'})
        self.assertEqual(W.load(s)['metrics']['state_align'],result['metrics']['state_align'])

    def test_small_valid_latent_measured_finite(self):
        s=Store()
        for i in range(24):s.add(i,chars=20+i,duration=.1+i*.01,output=10+i,route=W.ACTIONS[i%4],latent=[i*.01,i*.03])
        result=W.fit(s,rng_seed=42)
        self.assertEqual(result['metrics']['state_align']['status'],'MEASURED')
        self.assertTrue(all(math.isfinite(v) for v in result['metrics']['state_align']['r2'].values()))

    def test_no_latent_unavailable_unchanged(self):
        s=Store()
        for i in range(24):s.add(i,chars=20+i,duration=.1+i*.01,output=10+i,route=W.ACTIONS[i%4])
        self.assertEqual(W.fit(s,rng_seed=42)['metrics']['state_align']['status'],'UNAVAILABLE')

    def test_dual_primal_parity(self):
        rng=np.random.default_rng(20261024)
        X=rng.normal(size=(9,20));Y=rng.normal(size=(9,3));T=rng.normal(size=(4,20))
        dual=W._align_predict(X,Y,T,1.)
        primal=T@W.ridge(X,Y,1.)
        np.testing.assert_allclose(dual,primal,atol=1e-10,rtol=1e-10)

    def test_primal_branch_parity(self):
        rng=np.random.default_rng(20261024)
        X=rng.normal(size=(20,3));Y=rng.normal(size=(20,3));T=rng.normal(size=(4,3))
        np.testing.assert_allclose(W._align_predict(X,Y,T,1.),T@W.ridge(X,Y,1.),atol=1e-12)


if __name__=='__main__':unittest.main()
