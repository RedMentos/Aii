"""QA fault-injection regressions for the JEPA predictor checkpoint boundary.

Run: cd v13/code && python -m unittest tests.test_online_predictor_restart_integrity
No GGUF, Android hardware, or promotion gate is exercised.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from v13.continuous_predictor import OnlinePredictor


class PredictorRestartIntegrityTests(unittest.TestCase):
    def test_failed_final_publish_preserves_last_committed_checkpoint(self):
        with tempfile.TemporaryDirectory() as home:
            p = OnlinePredictor(2, 2, home, replay=4, seed=7)
            p.observe([0.1, 0.2], 0, [0.2, 0.3], rehearsals=0)
            p.checkpoint(["t8:first"])
            committed = p.path.read_bytes()
            p.observe([0.3, 0.4], 1, [0.4, 0.5], rehearsals=0)
            original_replace = __import__("os").replace

            def fail_publish(src, dst):
                if Path(dst) == p.path:
                    raise OSError("simulated final publish interruption")
                return original_replace(src, dst)

            with patch("v13.continuous_predictor.os.replace", side_effect=fail_publish):
                with self.assertRaisesRegex(OSError, "simulated final publish"):
                    p.checkpoint(["t8:first", "t8:second"])
            self.assertEqual(p.path.read_bytes(), committed)
            restarted = OnlinePredictor(2, 2, home, replay=4, seed=999)
            self.assertEqual(restarted.checkpoint_ids, ["t8:first"])
            self.assertEqual(restarted.seen, 1)

    def test_invalid_rng_checkpoint_does_not_publish_partial_restore(self):
        with tempfile.TemporaryDirectory() as home:
            p = OnlinePredictor(2, 2, home, replay=4, seed=7)
            p.observe([0.1, 0.2], 0, [0.2, 0.3], rehearsals=0)
            p.checkpoint(["t8:first"])
            p.observe([0.3, 0.4], 1, [0.4, 0.5], rehearsals=0)
            before = (p.W.copy(), p.U.copy(), p.bias.copy(), p.seen, p.updates)
            with np.load(p.path, allow_pickle=False) as data:
                fields = {key: data[key].copy() for key in data.files}
            fields["rng_state"] = np.array('{"invalid":true}')
            np.savez_compressed(p.path, **fields)
            with self.assertRaisesRegex(ValueError, "Invalid predictor checkpoint RNG state"):
                p.restore()
            np.testing.assert_array_equal(p.W, before[0])
            np.testing.assert_array_equal(p.U, before[1])
            np.testing.assert_array_equal(p.bias, before[2])
            self.assertEqual((p.seen, p.updates), before[3:])

    def test_rollback_is_explicitly_memory_only_until_new_checkpoint(self):
        with tempfile.TemporaryDirectory() as home:
            p = OnlinePredictor(2, 2, home, replay=4, seed=7)
            p.observe([0.1, 0.2], 0, [0.2, 0.3], rehearsals=0)
            p.checkpoint(["t8:first"])
            p.observe([0.3, 0.4], 1, [0.4, 0.5], rehearsals=0)
            p.checkpoint(["t8:first", "t8:second"])
            p.rollback()
            self.assertEqual(p.checkpoint_ids, ["t8:first"])
            self.assertEqual(p.seen, 1)
            restarted = OnlinePredictor(2, 2, home, replay=4, seed=999)
            self.assertEqual(restarted.checkpoint_ids, ["t8:first", "t8:second"])
            self.assertEqual(restarted.seen, 2)


if __name__ == "__main__":
    unittest.main()
