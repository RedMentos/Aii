"""An overflowed squared loss must never publish partial predictor learning."""
import tempfile
import unittest
import numpy as np
from v13.continuous_predictor import OnlinePredictor


class NonfiniteLossAtomicTests(unittest.TestCase):
    def test_overflowed_loss_rolls_back_all_mutable_state(self):
        with tempfile.TemporaryDirectory() as home:
            p = OnlinePredictor(1, 2, home, lr=0.02, replay=8, seed=17)
            p.W[0, 0] = 1e155
            p.checkpoint(processed_ids=['trusted:t8:1'])
            before = (p.W.copy(), p.U.copy(), p.bias.copy(), p.x.copy(),
                      p.act.copy(), p.y.copy(), p.seen, p.updates,
                      repr(p.rng.bit_generator.state), list(p.checkpoint_ids))
            with self.assertRaisesRegex(ValueError, 'Nonfinite online loss'):
                p.observe(np.array([1.]), 0, np.array([0.]), rehearsals=1)
            after = (p.W, p.U, p.bias, p.x, p.act, p.y, p.seen, p.updates,
                     repr(p.rng.bit_generator.state), p.checkpoint_ids)
            for i in range(6):
                np.testing.assert_array_equal(before[i], after[i])
            self.assertEqual(before[6:], after[6:])
            q = OnlinePredictor(1, 2, home, lr=0.02, replay=8, seed=99)
            self.assertEqual(q.seen, 0)
            self.assertEqual(q.checkpoint_ids, ['trusted:t8:1'])

    def test_normal_observation_reports_finite_loss(self):
        with tempfile.TemporaryDirectory() as home:
            p = OnlinePredictor(1, 2, home, replay=8)
            result = p.observe(np.array([0.2]), 1, np.array([0.4]), rehearsals=1)
            self.assertTrue(np.isfinite(result['loss']))
            self.assertEqual(result['seen'], 1)
            self.assertEqual(result['updates'], 2)


if __name__ == '__main__':
    unittest.main()
