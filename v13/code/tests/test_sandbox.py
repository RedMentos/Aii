"""WP-DS1 lab sandbox: world rules, Dirichlet information gain, policies run end to end. No models needed."""
import random
import unittest
from v13 import sandbox as S

class SandboxTests(unittest.TestCase):
    def test_tables_are_distributions(self):
        for w,acts in S.TRUE.items():
            for a,p in acts.items():self.assertAlmostEqual(sum(p),1.,9,(w,a))
    def test_digamma_matches_known_values(self):
        self.assertAlmostEqual(S.digamma(1.),-0.5772156649,7);self.assertAlmostEqual(S.digamma(.5),-1.9635100260,7)
    def test_eig_shrinks_with_evidence_and_is_zero_free(self):
        a=[S.ALPHA0]*S.K;e0=S.eig(a);a[1]+=20;self.assertLess(S.eig(a),e0);self.assertGreaterEqual(S.eig(a),0.)
    def test_noisy_tv_eig_also_vanishes(self):
        """Unlike prediction error, information gain on pure noise goes to zero once the noise is known."""
        a=[S.ALPHA0+200]*S.K;self.assertLess(S.eig(a),.01)
    def test_path_reaches_neighbour_cell(self):
        w=S.World(random.Random(3));oid,o=next(iter(w.objs.items()));p=w.path(o['cell'])
        self.assertIsNotNone(p);end=p[-1] if p else w.agent
        self.assertEqual(abs(end[0]-o['cell'][0])+abs(end[1]-o['cell'][1]),1)
    def test_every_policy_runs_and_is_seed_deterministic(self):
        for pol in S.POLICIES:
            a=S.run(pol,5,steps=200,new_kind_at=100);b=S.run(pol,5,steps=200,new_kind_at=100)
            self.assertEqual(a,b);self.assertEqual(a['steps'],200);self.assertGreater(a['interactions'],0)
    def test_learning_lowers_model_error(self):
        r=S.run('novelty',7,steps=600,new_kind_at=None);self.assertLess(r['curve'][-1][1],r['curve'][0][1])

if __name__=='__main__':unittest.main()
