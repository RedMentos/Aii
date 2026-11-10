"""Synthetic regression for overflowing first-step gradient admission.

Run: cd v13/code && python -m unittest tests.test_online_predictor_gradient_preflight
No native/Android or full JEPA claim.
"""
import tempfile
import unittest
import numpy as np
from v13.continuous_predictor import OnlinePredictor


class GradientPreflightTests(unittest.TestCase):
    def test_overflowing_norm_does_not_commit_replay_or_counters(self):
        with tempfile.TemporaryDirectory() as home:
            p = OnlinePredictor(1, 2, home, replay=4, seed=11)
            # Finite prediction and finite residual; squaring the residual
            # overflows float64, so the gradient norm is nonfinite.
            p.W[0, 0] = 1e200
            before = (p.seen, p.updates, p.x.copy(), p.act.copy(),
                      p.y.copy(), p.W.copy(), p.U.copy(), p.bias.copy())
            with self.assertRaisesRegex(ValueError, 'Nonfinite online gradient'):
                p.observe([1.0], 0, [0.0], rehearsals=0)
            self.assertEqual((p.seen, p.updates), before[:2])
            for actual, expected in zip((p.x, p.act, p.y, p.W, p.U, p.bias), before[2:]):
                np.testing.assert_array_equal(actual, expected)

    def test_normal_observation_still_updates(self):
        with tempfile.TemporaryDirectory() as home:
            p = OnlinePredictor(1, 2, home, replay=4, seed=11)
            result = p.observe([0.5], 0, [0.25], rehearsals=0)
            self.assertEqual(result['seen'], 1)
            self.assertEqual(result['updates'], 1)


if __name__ == '__main__':
    unittest.main()
