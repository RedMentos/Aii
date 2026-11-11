"""Reject checkpoint tensor dtype substitution without mutating active predictor.

Synthetic NumPy regression; no Android or model-weight claim.
"""
import tempfile
import unittest

import numpy as np

from v13.continuous_predictor import OnlinePredictor


class CheckpointDtypeQATests(unittest.TestCase):
    def test_complex_or_integer_weights_are_rejected_atomically(self):
        for dtype in ("complex128", "int64"):
            with self.subTest(dtype=dtype), tempfile.TemporaryDirectory() as home:
                model = OnlinePredictor(2, 2, home, replay=4, seed=3)
                model.observe([0.1, 0.2], 0, [0.2, 0.3], rehearsals=0)
                model.checkpoint(["t8:one"])
                with np.load(model.path, allow_pickle=False) as source:
                    payload = {key: source[key].copy() for key in source.files}
                payload["W"] = payload["W"].astype(dtype)
                np.savez_compressed(model.path, **payload)
                previous = (model.W.copy(), model.U.copy(), model.bias.copy(),
                            model.seen, model.updates, list(model.checkpoint_ids),
                            model.rng.bit_generator.state)
                with self.assertRaisesRegex(ValueError, "Invalid predictor checkpoint"):
                    model.restore()
                np.testing.assert_array_equal(model.W, previous[0])
                np.testing.assert_array_equal(model.U, previous[1])
                np.testing.assert_array_equal(model.bias, previous[2])
                self.assertEqual((model.seen, model.updates), previous[3:5])
                self.assertEqual(model.checkpoint_ids, previous[5])
                self.assertEqual(model.rng.bit_generator.state, previous[6])
                with self.assertRaisesRegex(ValueError, "Invalid predictor checkpoint"):
                    OnlinePredictor(2, 2, home, replay=4, seed=7)


if __name__ == "__main__":
    unittest.main()
