"""Tests for M1 baselines and common input-information parity."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta

import numpy as np
import torch

from v14.m1.array_data import ArrayDataset, InputBundle
from v14.m1.baselines import (
    LinearInputBaseline,\n    RidgeAR,
    PersistenceBaseline,
    RandomEncoderProbe,
    RawGRU,
    RawWindowMLP,
    SeasonalPersistenceBaseline,
    TrainConstantBaseline,
)
from v14.m1.base import BaseConfig
from v14.m1.data import DataConfig, MinuteRow\nfrom v14.m1.training import FitConfig, fit_supervised_baseline


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.bundle = InputBundle(
            x=np.arange(5 * 4 * 2, dtype=np.float32).reshape(5, 4, 2),
            seasonal=np.arange(5 * 3 * 2 * 2, dtype=np.float32).reshape(5, 3, 2, 2),
            calendar=np.zeros((5, 3, 4), dtype=np.float32),
        )
        self.width = 4 * 2 + 3 * 2 * 2 + 3 * 4

    def test_persistence_and_seasonal_persistence_shapes(self):
        p = PersistenceBaseline(horizon=3)(self.bundle)
        self.assertEqual(tuple(p.shape), (5, 3, 2))
        self.assertTrue(torch.equal(p[:, 0], p[:, 2]))
        s = SeasonalPersistenceBaseline(lag_index=1)(self.bundle)
        self.assertEqual(tuple(s.shape), (5, 3, 2))
        torch.testing.assert_close(s, torch.as_tensor(self.bundle.seasonal[:, :, 1, :]))

    def test_linear_mlp_and_gru_receive_common_bundle(self):
        models = [
            LinearInputBaseline(self.width, 3, 2),
            RawWindowMLP(self.width, 3, 2, hidden_dim=16),
            RawGRU(channels=2, seasonal_lags=2, horizon=3, hidden_dim=16),
        ]
        for model in models:
            result = model(self.bundle)
            self.assertEqual(tuple(result.shape), (5, 3, 2))

    def test_random_encoder_probe_shape_and_frozen_parameters(self):
        cfg = BaseConfig(channels=2, horizon=3, latent_dim=16, hidden_dim=32)
        model = RandomEncoderProbe(cfg)
        result = model(self.bundle)
        self.assertEqual(tuple(result.shape), (5, 3, 2))
        self.assertTrue(all(p.grad is None for p in model.encoder.parameters()))

    def test_ridge_baseline_can_be_fitted_with_mse_and_explicit_l2(self):
        start = datetime(2020, 1, 1)
        rows = [
            MinuteRow(start + timedelta(minutes=i), (float(np.sin(i / 10)), float(np.cos(i / 15))))
            for i in range(1000)
        ]
        config = DataConfig(
            input_length=5, horizon=2, max_candidate_input_length=5,
            seasonal_lags=(2, 4), train_fraction=0.70, validation_fraction=0.15,
        )
        dataset = ArrayDataset(rows, ("a", "b"), config)
        model = RidgeAR(dataset.input_width, 2, 2)
        report = fit_supervised_baseline(
            model, dataset, FitConfig(epochs=1, batch_size=64, patience=1, weight_decay=0.0),
            objective="mse", l2_penalty=1e-5,
        )
        self.assertEqual(report.validation_metric, "MAE")
        self.assertTrue(np.isfinite(report.best_validation_score))

    def test_train_mean_and_median_use_training_rows_only(self):
        start = datetime(2020, 1, 1)
        rows = [
            MinuteRow(start + timedelta(minutes=i), (float(i), float(2 * i)))
            for i in range(1000)
        ]
        config = DataConfig(
            input_length=5, horizon=2, max_candidate_input_length=5,
            seasonal_lags=(2, 4), train_fraction=0.70, validation_fraction=0.15,
        )
        dataset = ArrayDataset(rows, ("a", "b"), config)
        mean = TrainConstantBaseline(2, 2, "mean").fit(dataset)
        median = TrainConstantBaseline(2, 2, "median").fit(dataset)
        self.assertLess(float(mean.constant[0]), 700.0)
        self.assertLess(float(median.constant[0]), 700.0)
        self.assertEqual(tuple(mean(self.bundle).shape), (5, 2, 2))


if __name__ == "__main__":
    unittest.main()
