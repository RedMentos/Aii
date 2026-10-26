"""Run439 RED-first: finite native embedding coordinates can overflow their norm.

Only external NumPy shadow-head integrity. No body weights, JEPA or native phone proof.
"""
import tempfile
import unittest
from pathlib import Path

import numpy as np
from v13 import learning_worker as W


class Run439ShadowEmbeddingNormIntegrity(unittest.TestCase):
    def test_finite_coordinates_with_overflowed_norm_are_rejected(self):
        raw = [[1e308, 1e308], [1.0, 2.0]]
        self.assertTrue(np.isfinite(np.asarray(raw)).all())
        with np.errstate(over="ignore", invalid="ignore"):
            with self.assertRaisesRegex(ValueError, "embedding.*norm|norm.*overflow"):
                W.features(raw)

    def test_shadow_train_refuses_overflow_before_candidate_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            inp = {"config": {}, "embeddings": [[1e308, 1e308]],
                   "labels": [0], "scaffold_labels": [0]}
            with np.errstate(over="ignore", invalid="ignore"):
                with self.assertRaises(ValueError):
                    W.train(inp, td)
            self.assertFalse((Path(td) / "candidate.npz").exists())
            self.assertFalse((Path(td) / "metrics.json").exists())

    def test_normal_range_normalization_is_unchanged(self):
        raw = np.asarray([[3., 4.], [0.1, -0.2], [0., 0.]], dtype=np.float64)
        expected = raw / np.maximum(
            np.linalg.norm(raw, axis=1, keepdims=True), 1e-12) * 8.
        self.assertTrue(np.array_equal(W.features(raw), np.column_stack([
            expected, np.ones(len(raw))])))
        self.assertEqual(W.features(raw).shape, (3, 3))

    def test_nonfinite_raw_coordinates_still_refused(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    W.features([[1.0, value]])


if __name__ == "__main__":
    unittest.main()
