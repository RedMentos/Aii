"""Run111 WP-DS2 compositional toy-world grounding, heldout phrase integrity."""
import math
import random
import unittest

from v13 import sandbox_composition as C


class CompositionRun111(unittest.TestCase):
    def test_hidden_world_distributions_are_normalized(self):
        for pair in C.PAIRS:
            for action in C.ACTIONS:
                p=C.true_dist(*pair,action)
                self.assertEqual(len(p),len(C.OUTCOMES))
                self.assertAlmostEqual(sum(p),1.,12)
                self.assertTrue(all(0<=x<=1 for x in p))

    def test_models_never_need_hidden_tables_to_predict_or_learn(self):
        m=C.DirichletModels()
        original_obj,original_sup=C.TRUE_OBJECT,C.TRUE_SUPPORT
        try:
            C.TRUE_OBJECT=None
            C.TRUE_SUPPORT=None
            for pair in C.TRAIN_PAIRS:
                for action in C.ACTIONS:
                    m.observe(pair,action,0)
            for policy in ('pair','object','factor'):
                p=m.predict(policy,C.HOLDOUT[0],'push')
                self.assertAlmostEqual(sum(p),1.,12)
                self.assertTrue(all(math.isfinite(x) and x>0 for x in p))
        finally:
            C.TRUE_OBJECT,C.TRUE_SUPPORT=original_obj,original_sup

    def test_heldout_pair_never_appears_in_training(self):
        self.assertTrue(set(C.HOLDOUT).isdisjoint(C.TRAIN_PAIRS))
        r=C.run(200,steps=600)
        self.assertEqual(sum(r['training_pairs'].values()),600)
        for pair in C.HOLDOUT:
            self.assertEqual(r['training_pairs'].get('|'.join(pair),0),0)
        self.assertEqual(set(r['covered_words']['objects']),set(C.OBJECTS))
        self.assertEqual(set(r['covered_words']['supports']),set(C.SUPPORTS))

    def test_seed_replay_is_exact_and_different_seed_changes_stream(self):
        a=C.run(201,steps=600)
        self.assertEqual(a,C.run(201,steps=600))
        self.assertNotEqual(a['stream_sha256'],C.run(202,steps=600)['stream_sha256'])

    def test_all_three_ablations_produce_finite_holdout_metrics(self):
        r=C.run(203,steps=600)
        self.assertEqual(set(r['heldout_kl']),{'pair','object','factor'})
        self.assertEqual(set(r['train_kl']),{'pair','object','factor'})
        for d in (r['heldout_kl'],r['train_kl']):
            self.assertTrue(all(math.isfinite(x) and x>=0 for x in d.values()))
        m=C.DirichletModels()
        self.assertEqual(m.predict('pair',C.HOLDOUT[0],'push'),[1/len(C.OUTCOMES)]*len(C.OUTCOMES))


if __name__=='__main__':
    unittest.main()
