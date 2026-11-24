"""Integration smoke: run the diagnostic against the repository's real A3 Projector."""
import unittest

import numpy as np

from v13.vision import Projector
from vision_counterfactual_probe import audit_a3_projector


class A3ProjectorCounterfactualIntegration(unittest.TestCase):
    def test_actual_a3_projector_can_be_audited_for_change_subspace_loss(self):
        rng = np.random.default_rng(91)
        train_x = rng.normal(size=(240, 8))
        target_map = rng.normal(size=(7, 6))
        train_y = train_x[:, 1:] @ target_map
        projector = Projector(ridge=1e-3).fit(train_x, train_y)

        labels = np.asarray([1, -1] * 50, dtype=np.int64)
        common = rng.normal(0.0, 0.35, size=(100, 4, 8))
        direction = np.zeros(8, dtype=np.float64)
        direction[0] = 1.0
        noise = rng.normal(0.0, 0.01, size=(100, 4, 8))
        delta = labels[:, None, None] * 0.2 * direction[None, None, :] + noise
        original = common + delta
        transformed = common - delta
        groups = [f"a3-source-{index:03d}" for index in range(100)]

        result = audit_a3_projector(
            projector, original, transformed, labels, groups, folds=5,
        )
        self.assertGreater(result["input_features"]["kappa"], 0.90)
        self.assertLess(result["a3_projector_output"]["kappa"], 0.05)
        self.assertFalse(result["projector_weights_persisted"])


if __name__ == "__main__":
    unittest.main()
