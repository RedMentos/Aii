"""Reject invalid in-memory predictor state without corrupting persisted generations."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from v13.continuous_predictor import OnlinePredictor


class InvalidLiveCheckpointTests(unittest.TestCase):
    def test_nonfinite_live_weights_leave_committed_bytes_and_cursor_untouched(self):
        with tempfile.TemporaryDirectory() as root:
            p = OnlinePredictor(2, 2, root, replay=8, seed=7)
            p.checkpoint(processed_ids=["trusted:t8:1"])
            p.observe(np.array([0.1, 0.2]), 0, np.array([0.2, 0.3]), rehearsals=0)
            p.checkpoint()
            before = p.path.read_bytes()
            previous = p.path.with_suffix(".previous.npz").read_bytes()
            p.W[0, 0] = np.inf
            with self.assertRaisesRegex(ValueError, "Invalid live predictor checkpoint state"):
                p.checkpoint(processed_ids=["trusted:t8:2"])
            self.assertEqual(p.path.read_bytes(), before)
            self.assertEqual(p.path.with_suffix(".previous.npz").read_bytes(), previous)
            self.assertFalse(p.path.with_name(p.path.name + ".tmp.npz").exists())
            restored = OnlinePredictor(2, 2, root, replay=8, seed=9)
            self.assertEqual(restored.checkpoint_ids, ["trusted:t8:1"])
            self.assertEqual(restored.seen, 1)

    def test_invalid_replay_counters_rejected_without_creating_checkpoint(self):
        with tempfile.TemporaryDirectory() as root:
            p = OnlinePredictor(2, 2, root, replay=8)
            p.seen = -1
            with self.assertRaisesRegex(ValueError, "Invalid live predictor checkpoint state"):
                p.checkpoint()
            self.assertFalse(p.path.exists())

    def test_valid_checkpoint_still_restores(self):
        with tempfile.TemporaryDirectory() as root:
            p = OnlinePredictor(2, 2, root, replay=8)
            p.observe(np.array([0.1, 0.2]), 1, np.array([0.3, 0.4]), rehearsals=0)
            p.checkpoint(processed_ids=["trusted:t8:valid"])
            q = OnlinePredictor(2, 2, root, replay=8)
            self.assertEqual(q.seen, 1)
            self.assertEqual(q.checkpoint_ids, ["trusted:t8:valid"])


if __name__ == "__main__":
    unittest.main()
