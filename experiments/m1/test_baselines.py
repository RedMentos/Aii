"""Streaming BASE baseline tests for V14 M1."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta

import numpy as np

from experiments.m1.array_data import ArrayDataset
from experiments.m1.baselines import (
    LADARBaseline,
    PersistenceBaseline,
    RidgeARBaseline,
    SeasonalPersistenceBaseline,
    TrainMeanBaseline,
    TrainMedianBaseline,
    evaluate_mae,
)
from experiments.m1.data import DataConfig, MinuteRow


def rows_for(n: int):
    start = datetime(2020, 1, 1)
    return [
        MinuteRow(
            start + timedelta(minutes=i),
            (float(i % 17), float(200 + (i % 11))),
        )
        for i in range(n)
    ]


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.rows = rows_for(1000)
        self.channels = ("Global_active_power", "Voltage")
        self.config = DataConfig(
            input_length=5, horizon=2, max_candidate_input_length=5,
            seasonal_lags=(2, 4), train_fraction=0.70, validation_fraction=0.15,
        )
        self.dataset = ArrayDataset(self.rows, self.channels, self.config)
        self.batch = next(self.dataset.iter_batches("train", batch_size=32))

    def test_persistence_repeats_last_observation(self):
        prediction = PersistenceBaseline().predict(self.batch)
        expected = np.repeat(self.batch.inputs.x[:, -1:, :], self.config.horizon, axis=1)
        np.testing.assert_array_equal(prediction, expected)

    def test_seasonal_persistence_uses_requested_lag_series(self):
        prediction = SeasonalPersistenceBaseline(lag_index=1).predict(self.batch)
        np.testing.assert_array_equal(prediction, self.batch.inputs.seasonal[:, :, 1, :])
        with self.assertRaises(ValueError):
            SeasonalPersistenceBaseline(lag_index=2).predict(self.batch)

    def test_train_mean_and_median_use_unique_accepted_target_rows(self):
        target_rows = np.zeros(self.dataset.n_rows, dtype=bool)
        steps = np.arange(1, self.config.horizon + 1)
        for batch in self.dataset.iter_batches("train", batch_size=64):
            target_rows[batch.origin_indices[:, None] + steps[None, :]] = True
        expected = self.dataset.values[target_rows].astype(np.float64)
        mean = TrainMeanBaseline().fit(self.dataset, batch_size=64)
        median = TrainMedianBaseline().fit(self.dataset, batch_size=64)
        np.testing.assert_allclose(mean.values, expected.mean(axis=0))
        np.testing.assert_allclose(median.values, np.median(expected, axis=0))
        self.assertEqual(mean.n_unique_target_rows, int(target_rows.sum()))
        self.assertEqual(median.n_unique_target_rows, int(target_rows.sum()))

    def test_ridge_ar_streams_train_batches_and_predicts_all_horizons_channels(self):
        model = RidgeARBaseline(alpha=1.0, ar_lags=(1, 2, 3)).fit(self.dataset, batch_size=64)
        prediction = model.predict(self.batch)
        self.assertEqual(prediction.shape, self.batch.target.shape)
        self.assertTrue(np.isfinite(prediction).all())
        self.assertGreater(model.n_train_windows, 0)
        self.assertEqual(model.selected_ar_lags, (1, 2, 3))

    def test_lad_ar_is_l1_objective_with_l2_penalty(self):
        model = LADARBaseline(
            alpha=0.01, ar_lags=(1, 2, 3), epochs=2, learning_rate=0.01
        ).fit(self.dataset, batch_size=64)
        prediction = model.predict(self.batch)
        self.assertEqual(prediction.shape, self.batch.target.shape)
        self.assertTrue(np.isfinite(prediction).all())
        self.assertEqual(len(model.epoch_losses), 2)
        self.assertTrue(all(np.isfinite(value) for value in model.epoch_losses))

    def test_mae_evaluator_reports_horizon_and_channel_metrics(self):
        result = evaluate_mae(PersistenceBaseline(), self.dataset, "validation", batch_size=32)
        self.assertEqual(result["split"], "validation")
        self.assertGreater(result["n_windows"], 0)
        self.assertEqual(len(result["per_horizon_mae"]), self.config.horizon)
        self.assertEqual(len(result["per_channel_mae"]), len(self.channels))
        self.assertTrue(np.isfinite(result["mae"]))

    def test_mae_evaluator_cannot_bypass_test_split_gate(self):
        with self.assertRaises(PermissionError):
            evaluate_mae(PersistenceBaseline(), self.dataset, "test", batch_size=32)


if __name__ == "__main__":
    unittest.main()
