"""Synthetic tests for common M1 metrics, paired evaluation and atomic result persistence."""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from experiments.m1.array_data import ArrayDataset
from experiments.m1.data import DataConfig, MinuteRow
from experiments.m1.metrics import evaluate_predictor, evaluate_suite, write_result_atomic


class ZeroPredictor:
    name = "zero"

    def predict(self, batch):
        return np.zeros_like(batch.target)


class ConstantOnePredictor:
    name = "one"

    def predict(self, batch):
        return np.ones_like(batch.target)


def fixture_dataset():
    start = datetime(2020, 1, 1)
    rows = [
        MinuteRow(start + timedelta(minutes=i), (1.0, 1.0))
        for i in range(1200)
    ]
    config = DataConfig(
        input_length=8, horizon=4, max_candidate_input_length=8,
        seasonal_lags=(4, 8), train_fraction=0.70, validation_fraction=0.15,
    )
    return ArrayDataset(rows, ("Global_active_power", "Voltage"), config)


class MetricTests(unittest.TestCase):
    def setUp(self):
        self.dataset = fixture_dataset()

    def test_prefix_horizons_and_primary_window_mae(self):
        result, series = evaluate_predictor(
            ZeroPredictor(), self.dataset, "validation", seed=11,
            primary_start=2, primary_end=4, report_horizons=(1, 2, 4), batch_size=31,
        )
        self.assertEqual(result["mae_at_horizons"], {"1": 1.0, "2": 1.0, "4": 1.0})
        self.assertEqual(result["primary_mae"], 1.0)
        self.assertEqual(result["n_windows"], len(series.primary_mae))
        self.assertTrue(np.all(series.primary_mae == 1.0))
        self.assertEqual(result["per_horizon_channel_mae"], [[1.0, 1.0]] * 4)

    def test_suite_pairs_models_and_seeds(self):
        runs = [
            (ZeroPredictor(), 11), (ZeroPredictor(), 22),
            (ConstantOnePredictor(), 11), (ConstantOnePredictor(), 22),
        ]
        result = evaluate_suite(
            runs, self.dataset, reference_model="one", code_commit="a" * 40,
            primary_start=2, primary_end=4, report_horizons=(1, 2, 4),
            block_days=1, n_resamples=50, batch_size=32,
        )
        self.assertEqual(len(result["runs"]), 4)
        self.assertEqual(result["paired_block_bootstrap"]["seed_ids"], [11, 22])
        self.assertAlmostEqual(result["paired_block_bootstrap"]["models"]["zero"]["delta_vs_reference"], 1.0)

    def test_suite_rejects_unverified_commit_string(self):
        with self.assertRaises(ValueError):
            evaluate_suite(
                [(ZeroPredictor(), 1)], self.dataset,
                reference_model="zero", code_commit="not-a-commit",
                primary_start=2, primary_end=4, report_horizons=(1, 2, 4),
            )

    def test_result_is_atomic_canonical_and_hashable(self):
        result = {
            "schema": "test",
            "value": 1.25,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            digest = write_result_atomic(result, path)
            raw = path.read_bytes()
            self.assertEqual(len(digest), 64)
            self.assertEqual(json.loads(raw), result)
            self.assertEqual(raw, b'{"schema":"test","value":1.25}\n')


if __name__ == "__main__":
    unittest.main()
