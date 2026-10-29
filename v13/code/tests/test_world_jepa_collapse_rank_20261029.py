"""World-JEPA collapse diagnostics must not report positive effective rank on zero variance.

NumPy software-only; no native weights, no Age/JEPA promotion.
"""
import unittest
import warnings
import numpy as np

from v13.world_jepa import WorldJEPA


class WorldJEPACollapseRank(unittest.TestCase):
    def _fit(self, X):
        X = np.asarray(X, dtype=float)
        A = np.eye(2)[np.arange(len(X)) % 2]
        return WorldJEPA(seed=7, ensemble=1).fit(X, A, X.copy(), steps=0)

    def test_all_zero_target_latents_report_zero_evidence_not_rank_one(self):
        X = np.zeros((4, 2))
        model = self._fit(X)
        with warnings.catch_warnings(record=True) as seen:
            warnings.simplefilter("always")
            stats = model.collapse_stats(X)
        self.assertEqual(stats["effective_rank"], 0.0)
        self.assertEqual(stats["min_std"], 0.0)
        self.assertIs(stats["collapsed"], True)
        self.assertFalse(any("invalid value" in str(w.message) for w in seen))

    def test_noncollapsed_target_latents_remain_finite_positive_rank(self):
        X = np.array([[0., 0.], [1., 0.], [0., 1.], [1., 1.]])
        model = self._fit(X)
        stats = model.collapse_stats(X)
        self.assertTrue(np.isfinite(stats["effective_rank"]))
        self.assertGreater(stats["effective_rank"], 0.0)
        self.assertGreater(stats["min_std"], 0.0)
        self.assertIs(stats["collapsed"], False)

    def test_constant_nonzero_latents_have_zero_rank_despite_roundoff(self):
        X = np.array([[0., 0.], [1., 0.], [0., 1.], [1., 1.]])
        model = self._fit(X)
        probe = np.repeat(X[0:1], 7, axis=0)
        latent = model.latent(probe)
        self.assertTrue(np.array_equal(latent, np.repeat(latent[0:1], 7, axis=0)))
        self.assertGreater(float(np.abs(latent).max()), 0.)
        stats = model.collapse_stats(probe)
        self.assertEqual(stats["effective_rank"], 0.0)
        self.assertIs(stats["collapsed"], True)

    def test_singleton_probe_rejected_as_unmeasurable(self):
        X = np.zeros((4, 2))
        model = self._fit(X)
        with self.assertRaises(ValueError):
            model.collapse_stats(np.zeros((1, 2)))

    def test_nonfinite_probe_rejected_as_unmeasurable(self):
        X = np.zeros((4, 2))
        model = self._fit(X)
        with self.assertRaises(ValueError):
            model.collapse_stats(np.array([[0., 0.], [float("nan"), 0.]]))


if __name__ == "__main__":
    unittest.main()
