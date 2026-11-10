"""Deterministic disjoint holdout/restart evidence for the local predictor.

This tests bounded NumPy predictor behavior, not full World-JEPA or GGUF learning.
Run: cd v13/code && python -m unittest tests.test_online_predictor_heldout_retention
"""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from v13.continuous_predictor import OnlinePredictor


def transition(index):
    # Deterministic independent sample IDs; no test item enters training/replay.
    x = np.array([np.sin(index * 0.13), np.cos(index * 0.17)], dtype=float)
    action = index % 2
    y = np.array([0.65 * x[0] + 0.12 * action,
                  0.55 * x[1] - 0.09 * action], dtype=float)
    return x, action, y


class HeldoutRetentionTests(unittest.TestCase):
    def test_disjoint_holdout_and_checkpoint_restart(self):
        train_ids = tuple(range(0, 60))
        holdout_ids = tuple(range(1000, 1020))
        self.assertFalse(set(train_ids) & set(holdout_ids))
        train = [transition(i) for i in train_ids]
        holdout = [transition(i) for i in holdout_ids]
        with tempfile.TemporaryDirectory() as root:
            learner = OnlinePredictor(2, 2, root, seed=17, replay=16)
            before = learner.error(holdout)
            for sample in train:
                learner.observe(*sample, rehearsals=2)
            after = learner.error(holdout)
            self.assertTrue(np.isfinite([before, after]).all())
            self.assertEqual(learner.seen, len(train))
            learner.checkpoint(processed_ids=["trusted-t8-60"])
            restored = OnlinePredictor(2, 2, root, seed=999, replay=16)
            self.assertEqual(restored.checkpoint_ids, ["trusted-t8-60"])
            self.assertEqual(restored.seen, learner.seen)
            self.assertEqual(restored.updates, learner.updates)
            self.assertAlmostEqual(restored.error(holdout), after, places=12)
            np.testing.assert_array_equal(restored.W, learner.W)
            np.testing.assert_array_equal(restored.U, learner.U)

    def test_replay_ablation_has_independent_equal_holdout(self):
        train = [transition(i) for i in range(40)]
        holdout = [transition(i) for i in range(200, 220)]
        with tempfile.TemporaryDirectory() as root:
            no_replay = OnlinePredictor(2, 2, Path(root) / "none",
                                        seed=5, replay=16)
            replay = OnlinePredictor(2, 2, Path(root) / "replay",
                                     seed=5, replay=16)
            for sample in train:
                no_replay.observe(*sample, rehearsals=0)
                replay.observe(*sample, rehearsals=2)
            self.assertEqual(no_replay.seen, replay.seen)
            self.assertEqual(no_replay.updates, 40)
            self.assertEqual(replay.updates, 120)
            self.assertTrue(np.isfinite(no_replay.error(holdout)))
            self.assertTrue(np.isfinite(replay.error(holdout)))
            # Deliberately no superiority assertion: ablation measures rather
            # than presupposes retention or utility.


if __name__ == "__main__":
    unittest.main()
