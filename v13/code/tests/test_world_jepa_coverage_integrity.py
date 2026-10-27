"""Preregistered WP-Z12b train-only confidence evidence; synthetic software only."""
import unittest
from unittest import mock
import numpy as np
from v13 import world_jepa as wj


class WorldJEPACoverageIntegrity(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(902)
        self.X = rng.normal(size=(16, 8))
        self.A = np.eye(3)[[0]*8 + [1]*8]
        self.m = wj.WorldJEPA(seed=4, ensemble=1).fit(
            self.X, self.A, self.X + .01, steps=0
        )

    def _controlled_evidence(self, spread=None, ood=None):
        self.m.predict = lambda X, A: (
            np.zeros((len(X), wj.Z)),
            np.zeros(len(X)) if spread is None else np.asarray(spread)[:len(X)]
        )
        self.m.ood = lambda X: (
            np.zeros(len(X)) if ood is None else np.asarray(ood)[:len(X)]
        )

    def test_unseen_action_cannot_borrow_claimed_counts(self):
        self._controlled_evidence()
        qx = self.X[:3]
        qa = np.eye(3)
        conf, labels = self.m.confidence(qx, qa, [1000, 1000, 1000])
        self.assertEqual(conf.shape, (3,))
        self.assertTrue(np.isfinite(conf).all())
        self.assertEqual(conf[2], 0.)
        self.assertEqual(labels[2], 'SIMULATION_UNCERTAIN')
        # Eight observed training transitions cannot be claimed as a thousand.
        self.assertLessEqual(conf[0], 1 - np.exp(-8/wj.COVER_N) + 1e-12)
        self.assertLessEqual(conf[1], 1 - np.exp(-8/wj.COVER_N) + 1e-12)

    def test_invalid_counts_are_never_support(self):
        self._controlled_evidence()
        qx = self.X[:4]
        qa = np.eye(3)[[0, 0, 0, 0]]
        conf, labels = self.m.confidence(qx, qa, [np.nan, np.inf, -1, True])
        self.assertTrue(np.array_equal(conf, np.zeros(4)))
        self.assertEqual(labels, ['SIMULATION_UNCERTAIN']*4)

    def test_invalid_actions_and_nonfinite_states_are_uncertain(self):
        self._controlled_evidence()
        qx = self.X[:4].copy()
        qx[3, 0] = np.nan
        qa = np.array([[0.,0.,0.],[1.,1.,0.],[np.nan,0.,0.],[1.,0.,0.]])
        conf, labels = self.m.confidence(qx, qa, [1000]*4)
        self.assertTrue(np.array_equal(conf, np.zeros(4)))
        self.assertEqual(labels, ['SIMULATION_UNCERTAIN']*4)

    def test_invalid_prediction_spread_and_ood_fail_closed(self):
        self._controlled_evidence(
            spread=[np.nan, np.inf, -1., 0.],
            ood=[0., 0., 0., np.nan]
        )
        qx = self.X[:4]
        qa = np.eye(3)[[0, 0, 0, 0]]
        conf, labels = self.m.confidence(qx, qa, [1000]*4)
        self.assertTrue(np.array_equal(conf, np.zeros(4)))
        self.assertEqual(labels, ['SIMULATION_UNCERTAIN']*4)

    def test_mismatched_batch_shapes_do_not_broadcast_coverage(self):
        self._controlled_evidence()
        with self.assertRaises(ValueError):
            self.m.confidence(self.X[:2], np.eye(3)[:1], [100, 100])
        with self.assertRaises(ValueError):
            self.m.confidence(self.X[:2], np.eye(3)[:2], [100])
        with self.assertRaises(ValueError):
            self.m.confidence(self.X[:2], np.eye(4)[:2], [100, 100])


if __name__ == '__main__':
    unittest.main()
