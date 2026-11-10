"""Adversarial checkpoint/restore boundaries for the real bounded predictor.

Synthetic NumPy tests only. No Android, GGUF, or Age gate promotion.
Run: cd v13/code && python -m unittest -v tests.test_online_predictor_adversarial_checkpoint
"""
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from v13.continuous_predictor import OnlinePredictor


class AdversarialCheckpointTests(unittest.TestCase):
    def _model(self, home):
        p = OnlinePredictor(2, 2, home, replay=4, seed=17)
        p.observe([0.1, 0.2], 0, [0.2, 0.3], rehearsals=0)
        p.checkpoint(["t8:trusted-1"])
        return p

    def test_failed_backup_copy_does_not_publish_new_checkpoint(self):
        with tempfile.TemporaryDirectory() as home:
            p = self._model(home)
            original = p.path.read_bytes()
            p.observe([0.4, 0.3], 1, [0.6, 0.5], rehearsals=0)
            with patch("v13.continuous_predictor.shutil.copy2",
                       side_effect=OSError("simulated backup copy failure")):
                with self.assertRaisesRegex(OSError, "backup copy failure"):
                    p.checkpoint(["t8:trusted-1", "t8:trusted-2"])
            self.assertEqual(p.path.read_bytes(), original)
            self.assertFalse(p.path.with_suffix(".previous.tmp.npz").exists())
            self.assertFalse(p.path.with_name(p.path.name + ".tmp.npz").exists())
            restored = OnlinePredictor(2, 2, home, replay=4, seed=99)
            self.assertEqual(restored.checkpoint_ids, ["t8:trusted-1"])
            self.assertEqual(restored.seen, 1)

    def test_float_replay_actions_rejected_without_partial_restore(self):
        with tempfile.TemporaryDirectory() as home:
            p = self._model(home)
            p.observe([0.4, 0.3], 1, [0.6, 0.5], rehearsals=0)
            before = (p.W.copy(), p.U.copy(), p.seen, p.updates, list(p.checkpoint_ids))
            with np.load(p.path, allow_pickle=False) as archive:
                fields = {name: archive[name].copy() for name in archive.files}
            fields["act"] = fields["act"].astype(np.float64)
            np.savez_compressed(p.path, **fields)
            with self.assertRaisesRegex(ValueError, "Invalid predictor checkpoint"):
                p.restore()
            np.testing.assert_array_equal(p.W, before[0])
            np.testing.assert_array_equal(p.U, before[1])
            self.assertEqual((p.seen, p.updates, p.checkpoint_ids), before[2:])

    def test_duplicate_t8_cursor_rejected_without_partial_restore(self):
        with tempfile.TemporaryDirectory() as home:
            p = self._model(home)
            p.observe([0.4, 0.3], 1, [0.6, 0.5], rehearsals=0)
            before = (p.W.copy(), p.seen, p.updates, list(p.checkpoint_ids))
            with np.load(p.path, allow_pickle=False) as archive:
                fields = {name: archive[name].copy() for name in archive.files}
            fields["processed_ids"] = np.array('["t8:trusted-1","t8:trusted-1"]')
            np.savez_compressed(p.path, **fields)
            with self.assertRaisesRegex(ValueError, "Invalid checkpoint action cursor"):
                p.restore()
            np.testing.assert_array_equal(p.W, before[0])
            self.assertEqual((p.seen, p.updates, p.checkpoint_ids), before[1:])


if __name__ == "__main__":
    unittest.main()
