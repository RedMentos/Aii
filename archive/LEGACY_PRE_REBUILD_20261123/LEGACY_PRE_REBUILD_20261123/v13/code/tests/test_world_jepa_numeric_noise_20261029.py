"""Deterministic finite target-latent roundoff must not fabricate World-JEPA rank.

Software-only synthetic diagnostic: no model learning, native weights, Redmi, or authority.
"""
import unittest
import numpy as np

from v13.world_jepa import WorldJEPA


class WorldJEPANumericNoise(unittest.TestCase):
    def setUp(self):
        self.X = np.array([[0., 0.], [1., 0.], [0., 1.], [1., 1.]])
        A = np.eye(2)[np.arange(len(self.X)) % 2]
        self.model = WorldJEPA(seed=7, ensemble=1).fit(self.X, A, self.X, steps=0)

    def test_finite_ulp_jitter_cannot_create_rank_from_constant_latent(self):
        probe = np.repeat(self.X[0:1], 7, axis=0)
        baseline = self.model.latent(probe)
        zt = np.repeat(baseline[0:1], 7, axis=0)
        original = float(zt[0, 0])
        self.assertNotEqual(original, 0.)
        # Two adjacent representable numbers around one nonzero latent
        # simulate BLAS-dependent reduction ordering without any random seed.
        zt[::2, 0] = np.nextafter(original, np.inf)
        zt[1::2, 0] = np.nextafter(original, -np.inf)
        self.assertGreater(float(np.ptp(zt[:, 0])), 0.)
        self.model.latent = lambda _probe: zt.copy()
        stats = self.model.collapse_stats(probe)
        self.assertEqual(stats["effective_rank"], 0.)
        self.assertIs(stats["collapsed"], True)

    def test_resolvable_nonconstant_latent_must_keep_positive_rank(self):
        probe = self.X.copy()
        zt = np.repeat(self.model.latent(probe[:1]), len(probe), axis=0)
        zt[1, 0] += 1e-6
        zt[2, 1] -= 1e-6
        self.model.latent = lambda _probe: zt.copy()
        stats = self.model.collapse_stats(probe)
        self.assertTrue(np.isfinite(stats["effective_rank"]))
        self.assertGreater(stats["effective_rank"], 0.)
        self.assertIs(stats["collapsed"], False)

    def test_unmodified_model_repeated_input_is_numerically_constant(self):
        probe = np.repeat(self.X[0:1], 7, axis=0)
        zt = self.model.latent(probe)
        np.testing.assert_allclose(zt, np.repeat(zt[0:1], len(probe), axis=0),
                                   rtol=0., atol=1e-12)
        stats = self.model.collapse_stats(probe)
        self.assertEqual(stats["effective_rank"], 0.)
        self.assertIs(stats["collapsed"], True)


if __name__ == "__main__":
    unittest.main()
