"""Reject invalid in-memory replay action routes before publishing checkpoint bytes."""
import tempfile
import unittest
import numpy as np
from v13.continuous_predictor import OnlinePredictor


class LiveReplayActionTests(unittest.TestCase):
    def test_corrupt_action_index_preserves_both_generations(self):
        with tempfile.TemporaryDirectory() as home:
            p = OnlinePredictor(2, 2, home, replay=8)
            p.checkpoint(processed_ids=["trusted:t8:before"])
            p.observe(np.array([0.1, 0.2]), 0, np.array([0.3, 0.4]), rehearsals=0)
            p.checkpoint()
            current = p.path.read_bytes()
            previous = p.path.with_suffix(".previous.npz").read_bytes()
            p.act[0] = 2
            with self.assertRaisesRegex(ValueError, "Invalid live predictor checkpoint state"):
                p.checkpoint(processed_ids=["trusted:t8:after"])
            self.assertEqual(p.path.read_bytes(), current)
            self.assertEqual(p.path.with_suffix(".previous.npz").read_bytes(), previous)
            self.assertFalse(p.path.with_name(p.path.name + ".tmp.npz").exists())
            restored = OnlinePredictor(2, 2, home, replay=8)
            self.assertEqual(restored.checkpoint_ids, ["trusted:t8:before"])
            self.assertEqual(restored.seen, 1)

    def test_float_action_array_rejected_before_first_checkpoint(self):
        with tempfile.TemporaryDirectory() as home:
            p = OnlinePredictor(2, 2, home, replay=8)
            p.act = np.array([0.0])
            p.x = np.zeros((1, 2))
            p.y = np.zeros((1, 2))
            p.seen = p.updates = 1
            with self.assertRaisesRegex(ValueError, "Invalid live predictor checkpoint state"):
                p.checkpoint()
            self.assertFalse(p.path.exists())

    def test_valid_replay_still_roundtrips(self):
        with tempfile.TemporaryDirectory() as home:
            p = OnlinePredictor(2, 2, home, replay=8)
            p.observe(np.array([0.1, 0.2]), 1, np.array([0.3, 0.4]), rehearsals=0)
            p.checkpoint()
            q = OnlinePredictor(2, 2, home, replay=8)
            self.assertEqual(q.seen, 1)
            self.assertEqual(q.act.tolist(), [1])


if __name__ == "__main__":
    unittest.main()
