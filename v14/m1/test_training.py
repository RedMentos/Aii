"""Small synthetic tests for the M1 training loops."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta

import numpy as np
import torch

from v14.m1.array_data import ArrayDataset
from v14.m1.base import BaseConfig, DirectMAE, FrozenRepresentationProbe, M1JEPA, VICRegControl
from v14.m1.data import DataConfig, MinuteRow
from v14.m1.training import FitConfig, fit_direct_mae, fit_frozen_probe, fit_jepa, fit_vicreg_control


class TrainingLoopTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(3)
        start = datetime(2020, 1, 1)
        rows = []
        for i in range(1000):
            value = float(np.sin(i / 20.0) + 0.2 * np.cos(i / 7.0))
            rows.append(MinuteRow(
                start + timedelta(minutes=i),
                (value, float(value * 0.5 + np.sin(i / 5.0) * 0.1)),
            ))
        cfg = DataConfig(
            input_length=5, horizon=2, max_candidate_input_length=5,
            seasonal_lags=(2, 4), train_fraction=0.70, validation_fraction=0.15,
        )
        self.dataset = ArrayDataset(rows, ("a", "b"), cfg)
        self.base_cfg = BaseConfig(channels=2, horizon=2, latent_dim=16, hidden_dim=32)
        self.fit_cfg = FitConfig(
            epochs=2, batch_size=64, learning_rate=1e-3,
            patience=2, collapse_weight=0.01,
        )

    def test_jepa_training_updates_online_and_ema_target(self):
        model = M1JEPA(self.base_cfg)
        before = next(model.target_encoder.parameters()).detach().clone()
        report = fit_jepa(model, self.dataset, self.fit_cfg)
        after = next(model.target_encoder.parameters()).detach()
        self.assertGreater(report.optimizer_steps, 0)
        self.assertGreater(report.best_epoch, 0)
        self.assertFalse(torch.equal(before, after))

    def test_vicreg_control_trains_from_two_augmented_views(self):
        model = VICRegControl(self.base_cfg)
        before = next(model.encoder.parameters()).detach().clone()
        report = fit_vicreg_control(
            model, self.dataset, self.fit_cfg, noise_std=0.005,
            channel_drop_probability=0.05, random_seed=11,
        )
        after = next(model.encoder.parameters()).detach()
        self.assertGreater(report.optimizer_steps, 0)
        self.assertEqual(report.validation_metric, "VICReg_objective")
        self.assertTrue(np.isfinite(report.best_validation_score))
        self.assertFalse(torch.equal(before, after))

    def test_unshared_recurrent_jepa_trains_from_scratch(self):
        config = BaseConfig(
            channels=2, horizon=2, latent_dim=16, hidden_dim=32,
            predictor_steps=2, predictor_kind="unshared",
        )
        model = M1JEPA(config)
        report = fit_jepa(model, self.dataset, self.fit_cfg)
        self.assertGreater(report.optimizer_steps, 0)
        self.assertEqual(report.validation_metric, "latent_prediction_L1")
        self.assertEqual(len(model.predictor.blocks), 2)

    def test_direct_mae_training_uses_validation_selection(self):
        model = DirectMAE(self.base_cfg)
        report = fit_direct_mae(model, self.dataset, self.fit_cfg)
        self.assertGreater(report.optimizer_steps, 0)
        self.assertTrue(np.isfinite(report.best_validation_score))

    def test_frozen_probe_does_not_update_encoder(self):
        source = M1JEPA(self.base_cfg)
        model = FrozenRepresentationProbe(source.context_encoder, self.base_cfg)
        before = [p.detach().clone() for p in model.encoder.parameters()]
        report = fit_frozen_probe(model, self.dataset, self.fit_cfg)
        self.assertGreater(report.optimizer_steps, 0)
        for old, current in zip(before, model.encoder.parameters(), strict=True):
            torch.testing.assert_close(old, current)
        self.assertTrue(np.isfinite(report.best_validation_score))


if __name__ == "__main__":
    unittest.main()
