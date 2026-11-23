"""Tests for forecast metrics and paired temporal-block bootstrap."""
from __future__ import annotations

import unittest
import numpy as np

from datetime import datetime, timedelta

from v14.m1.array_data import ArrayDataset
from v14.m1.baselines import PersistenceBaseline
from v14.m1.data import DataConfig, MinuteRow
from v14.m1.evaluation import (
    collect_model_errors, forecast_metrics, paired_block_bootstrap,
    per_window_primary_mae,
)


class EvaluationTests(unittest.TestCase):
    def test_primary_endpoint_is_all_lead_times_15_through_60(self):
        target = np.zeros((2, 60, 3), dtype=np.float32)
        prediction = np.zeros_like(target)
        prediction[:, 14:60, :] = 2.0
        prediction[:, 0:14, :] = 100.0
        report = forecast_metrics(target, prediction)
        self.assertEqual(report.mae_at_15, 2.0)
        self.assertEqual(report.mae_at_30, 2.0)
        self.assertEqual(report.mae_at_60, 2.0)
        self.assertEqual(report.primary_mae_15_60, 2.0)
        np.testing.assert_allclose(per_window_primary_mae(target, prediction), [2.0, 2.0])

    def test_bootstrap_uses_temporal_blocks_and_averages_seeds(self):
        origins = np.arange(0, 10000, 10, dtype=np.int64)
        base = np.linspace(0.5, 1.5, origins.size)
        a = np.stack((base + 0.1, base + 0.2))
        b = np.stack((base + 0.3, base + 0.5))
        result = paired_block_bootstrap(
            {"JEPA": a, "Persistence": b}, origins, "JEPA", "Persistence",
            block_length=1000, n_bootstrap=200, random_seed=5,
        )
        self.assertEqual(result.block_count, 10)
        self.assertEqual(result.bootstrap_replicates, 200)
        self.assertAlmostEqual(result.point_difference_a_minus_b, -0.25, places=6)
        self.assertEqual(len(result.per_seed_differences), 2)
        self.assertGreater(result.seed_difference_std, 0.0)
        self.assertLess(result.confidence_interval_high, 0.0)

    def test_streaming_error_collection_uses_validation_and_keeps_test_locked(self):
        start = datetime(2020, 1, 1)
        rows = [
            MinuteRow(start + timedelta(minutes=i), (float(i % 37), float(i % 19)))
            for i in range(2000)
        ]
        config = DataConfig(
            input_length=5, horizon=60, max_candidate_input_length=5,
            seasonal_lags=(60, 120), train_fraction=0.70, validation_fraction=0.15,
        )
        dataset = ArrayDataset(rows, ("a", "b"), config)
        model = PersistenceBaseline(horizon=60)
        errors = collect_model_errors(model, dataset, split="validation", batch_size=16)
        self.assertGreater(errors.origin_indices.size, 0)
        self.assertEqual(errors.primary_mae.shape, errors.origin_indices.shape)
        self.assertEqual(errors.mae_at_60.shape, errors.origin_indices.shape)
        with self.assertRaises(PermissionError):
            collect_model_errors(model, dataset, split="test", batch_size=16)

    def test_bootstrap_rejects_misaligned_seeds_or_origins(self):
        with self.assertRaises(ValueError):
            paired_block_bootstrap(
                {"A": np.zeros((2, 5)), "B": np.zeros((1, 5))},
                np.arange(5), "A", "B", block_length=2,
            )


if __name__ == "__main__":
    unittest.main()
