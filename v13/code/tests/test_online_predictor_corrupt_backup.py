"""Rollback failure isolation for malformed predictor backup snapshots.

Synthetic NumPy-only QA. A malformed previous generation must not partially
replace the active in-memory predictor, and the active checkpoint must survive.
"""
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np

from v13.continuous_predictor import OnlinePredictor


class CorruptBackupRollbackTests(unittest.TestCase):
    def test_corrupt_backup_does_not_mutate_live_predictor(self):
        with tempfile.TemporaryDirectory() as home:
            model = OnlinePredictor(2, 2, home, replay=4, seed=7)
            model.observe([0.1, 0.2], 0, [0.2, 0.3], rehearsals=0)
            model.checkpoint(["t8:old"])
            model.observe([0.3, 0.4], 1, [0.4, 0.5], rehearsals=0)
            model.checkpoint(["t8:old", "t8:new"])
            current_bytes = model.path.read_bytes()
            old_backup = model.path.with_suffix(".previous.npz")
            old_backup.write_bytes(b"not an npz archive")
            before = (model.W.copy(), model.U.copy(), model.bias.copy(),
                      model.x.copy(), model.act.copy(), model.y.copy(),
                      model.seen, model.updates, list(model.checkpoint_ids),
                      model.rng.bit_generator.state)
            with self.assertRaises((ValueError, OSError, zipfile.BadZipFile)):
                model.rollback()
            self.assertEqual(model.path.read_bytes(), current_bytes)
            self.assertEqual(model.path, Path(home) / "online_predictor.npz")
            for actual, expected in zip(
                (model.W, model.U, model.bias, model.x, model.act, model.y),
                before[:6],
            ):
                np.testing.assert_array_equal(actual, expected)
            self.assertEqual((model.seen, model.updates), before[6:8])
            self.assertEqual(model.checkpoint_ids, before[8])
            self.assertEqual(model.rng.bit_generator.state, before[9])
            # Failed rollback must not break subsequent recovery of live checkpoint.
            restarted = OnlinePredictor(2, 2, home, replay=4, seed=99)
            self.assertEqual(restarted.checkpoint_ids, ["t8:old", "t8:new"])
            self.assertEqual(restarted.seen, 2)


if __name__ == "__main__":
    unittest.main()
