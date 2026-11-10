"""Synthetic regression: failed rehearsal must not publish a partial transition.

Run: cd v13/code && python -m unittest tests.test_online_predictor_rehearsal_atomic
"""
import json
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from v13.continuous_predictor import OnlinePredictor


class RehearsalAtomicTests(unittest.TestCase):
    def test_later_gradient_failure_rolls_back_every_mutable_field(self):
        with tempfile.TemporaryDirectory() as home:
            p = OnlinePredictor(2, 2, home, replay=4, seed=19)
            p.observe([0.1, 0.2], 0, [0.2, 0.3], rehearsals=0)
            before = (p.W.copy(), p.U.copy(), p.bias.copy(), p.x.copy(),
                      p.act.copy(), p.y.copy(), p.seen, p.updates,
                      json.dumps(p.rng.bit_generator.state))
            norm = np.linalg.norm
            calls = [0]

            def fail_later_gradient(vector):
                calls[0] += 1
                if calls[0] == 3:
                    return float('inf')
                return norm(vector)

            with patch('v13.continuous_predictor.np.linalg.norm',
                       side_effect=fail_later_gradient):
                with self.assertRaisesRegex(ValueError, 'Nonfinite online gradient'):
                    p.observe([0.3, 0.4], 1, [0.4, 0.5], rehearsals=2)
            self.assertEqual(calls[0], 3)
            for actual, expected in zip(
                (p.W, p.U, p.bias, p.x, p.act, p.y), before[:6]
            ):
                np.testing.assert_array_equal(actual, expected)
            self.assertEqual((p.seen, p.updates), before[6:8])
            self.assertEqual(json.dumps(p.rng.bit_generator.state), before[8])

    def test_successful_rehearsal_still_commits(self):
        with tempfile.TemporaryDirectory() as home:
            p = OnlinePredictor(2, 2, home, replay=4, seed=19)
            result = p.observe([0.1, 0.2], 0, [0.2, 0.3], rehearsals=2)
            self.assertEqual(result['seen'], 1)
            self.assertEqual(result['updates'], 3)


if __name__ == '__main__':
    unittest.main()
