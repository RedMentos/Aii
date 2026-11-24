import unittest

import numpy as np

from vision_counterfactual_probe import (
    audit_a3_projector,
    measure_counterfactual_change,
    project_a3_sequences,
    source_disjoint_folds,
)


class VisionCounterfactualProbeTests(unittest.TestCase):
    def _shared_change_data(self, n=120, seed=9):
        rng = np.random.default_rng(seed)
        labels = np.asarray([1, -1] * (n // 2), dtype=np.int64)
        rng.shuffle(labels)
        common = rng.normal(0.0, 0.35, size=(n, 4, 8))
        direction = np.asarray([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        magnitude = 0.22
        noise = rng.normal(0.0, 0.015, size=(n, 4, 8))
        delta = labels[:, None, None] * magnitude * direction[None, None, :] + noise
        original = common + delta
        transformed = common - delta
        groups = [f"clip-{i:03d}" for i in range(n)]
        return original, transformed, labels, groups

    def test_predictive_change_direction_is_readable_on_source_disjoint_holdout(self):
        original, transformed, labels, groups = self._shared_change_data()
        result = measure_counterfactual_change(original, transformed, labels, groups, folds=5)
        self.assertEqual(result["status"], "SHARED_CHANGE_CANDIDATE")
        self.assertEqual(result["split"], "SOURCE_DISJOINT")
        self.assertGreater(result["kappa"], 0.90)
        self.assertGreater(result["change_linear_probe_accuracy"], 0.95)
        self.assertLess(result["content_linear_probe_accuracy"], 0.70)
        self.assertFalse(result["fitted_weights_persisted"])

    def test_framewise_reversal_after_inverse_token_alignment_has_no_in_token_change(self):
        rng = np.random.default_rng(4)
        original = rng.normal(size=(40, 6, 12))
        transformed_raw = original[:, ::-1, :]
        transformed_aligned = transformed_raw[:, ::-1, :]
        labels = np.asarray([1, -1] * 20)
        groups = [f"source-{i:02d}" for i in range(40)]
        result = measure_counterfactual_change(original, transformed_aligned, labels, groups, folds=4)
        self.assertEqual(result["status"], "NO_CHANGE_COMPONENT")
        self.assertLess(result["r_d"], 1e-10)
        self.assertEqual(result["kappa"], 0.0)

    def test_shuffled_answer_sign_is_negative_control(self):
        original, transformed, labels, groups = self._shared_change_data(n=160, seed=21)
        shuffled = np.random.default_rng(33).permutation(labels)
        result = measure_counterfactual_change(original, transformed, shuffled, groups, folds=5, seed=8)
        self.assertLess(result["kappa"], 0.03)
        self.assertLess(result["change_linear_probe_accuracy"], 0.70)

    def test_source_groups_never_cross_folds(self):
        groups = [f"source-{i // 2:02d}" for i in range(40)]
        folds = source_disjoint_folds(groups, folds=5)
        for train, test in folds:
            self.assertFalse(set(groups[i] for i in train) & set(groups[i] for i in test))

    def test_a3_projector_audit_detects_removed_change_subspace(self):
        original, transformed, labels, groups = self._shared_change_data(n=100, seed=12)
        matrix = np.eye(8, dtype=np.float64)
        matrix[0, 0] = 0.0
        def projector(values):
            return values @ matrix
        projected = project_a3_sequences(projector, original)
        self.assertEqual(projected.shape, original.shape)
        result = audit_a3_projector(projector, original, transformed, labels, groups, folds=5)
        self.assertGreater(result["input_features"]["kappa"], 0.90)
        self.assertLess(result["a3_projector_output"]["kappa"], 0.03)
        self.assertLess(result["kappa_retention_ratio"], 0.05)

    def test_invalid_shapes_nonfinite_and_nonbinary_labels_fail_closed(self):
        original, transformed, labels, groups = self._shared_change_data(n=20)
        with self.assertRaises(ValueError):
            measure_counterfactual_change(original, transformed[:, :, :-1], labels, groups, folds=2)
        broken = original.copy()
        broken[0, 0, 0] = np.nan
        with self.assertRaises(ValueError):
            measure_counterfactual_change(broken, transformed, labels, groups, folds=2)
        with self.assertRaises(ValueError):
            measure_counterfactual_change(original, transformed, np.zeros(20), groups, folds=2)


if __name__ == "__main__":
    unittest.main()
