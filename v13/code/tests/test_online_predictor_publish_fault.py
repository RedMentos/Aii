"""Fault injection at the final checkpoint publication boundary.

Synthetic-only tests. No native model, Android, or learning-gate claims.
"""
import os
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from v13.continuous_predictor import OnlinePredictor


class PublishFaultTests(unittest.TestCase):
    def test_final_replace_failure_preserves_committed_checkpoint_and_cursor(self):
        with tempfile.TemporaryDirectory() as home:
            model = OnlinePredictor(2, 2, home, replay=4, seed=7)
            model.observe([0.1, 0.2], 0, [0.2, 0.3], rehearsals=0)
            model.checkpoint(["t8:old"])
            original = model.path.read_bytes()
            old_ids = list(model.checkpoint_ids)
            model.observe([0.3, 0.4], 1, [0.4, 0.5], rehearsals=0)
            real_replace = os.replace

            def fail_only_publish(src, dst):
                if str(dst) == str(model.path):
                    raise OSError("injected publish failure")
                return real_replace(src, dst)

            with patch("v13.continuous_predictor.os.replace", side_effect=fail_only_publish):
                with self.assertRaisesRegex(OSError, "injected publish failure"):
                    model.checkpoint(["t8:old", "t8:new"])
            self.assertEqual(model.path.read_bytes(), original)
            self.assertEqual(model.checkpoint_ids, old_ids)
            self.assertFalse(model.path.with_name(model.path.name + ".tmp.npz").exists())
            backup = model.path.with_suffix(".previous.npz")
            self.assertEqual(backup.read_bytes(), original)
            restarted = OnlinePredictor(2, 2, home, replay=4, seed=99)
            self.assertEqual(restarted.checkpoint_ids, ["t8:old"])
            self.assertEqual(restarted.seen, 1)

    def test_rejected_cursor_does_not_touch_committed_bytes(self):
        with tempfile.TemporaryDirectory() as home:
            model = OnlinePredictor(2, 2, home, replay=4, seed=7)
            model.checkpoint(["t8:old"])
            original = model.path.read_bytes()
            with self.assertRaisesRegex(ValueError, "Invalid committed action cursor"):
                model.checkpoint(["t8:old", "t8:old"])
            self.assertEqual(model.path.read_bytes(), original)
            self.assertEqual(model.checkpoint_ids, ["t8:old"])


if __name__ == "__main__":
    unittest.main()
