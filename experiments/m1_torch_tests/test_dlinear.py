"""CPU tests for the matched-information DLinear control."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta

import numpy as np
import torch

from experiments.m1.array_data import ArrayDataset
from experiments.m1.data import DataConfig, MinuteRow
from experiments.m1.dlinear import (
    MatchedDLinearForecaster,
    MatchedNLinearForecaster,
    MovingAverageDecomposition,
)
from experiments.m1.jepa import JEPAConfig
from experiments.m1.training import build_seeded_model, train_direct_mae


def fixture_dataset():
    start = datetime(2021, 1, 1)
    rows = []
    for i in range(1200):
        daily = np.sin(2.0 * np.pi * (i % 1440) / 1440.0)
        weekly = np.cos(2.0 * np.pi * (i % 10080) / 10080.0)
        rows.append(MinuteRow(
            start + timedelta(minutes=i),
            (float(1.5 + 0.4 * daily + 0.05 * np.sin(i / 13.0)),
             float(220.0 + 3.0 * weekly + 0.2 * np.cos(i / 17.0))),
        ))
    data_config = DataConfig(
        input_length=8, horizon=4, max_candidate_input_length=8,
        seasonal_lags=(4, 8), train_fraction=0.70, validation_fraction=0.15,
    )
    return ArrayDataset(rows, ("Global_active_power", "Voltage"), data_config)


def model_config():
    return JEPAConfig(
        input_channels=2, seasonal_lags=2, horizon=4, calendar_features=4,
        patch_size=2, d_model=8, n_heads=2, encoder_layers=1,
        predictor_layers=1, dropout=0.0, ema_start=0.5, ema_end=0.9,
    )


class DLinearTests(unittest.TestCase):
    def setUp(self):
        self.dataset = fixture_dataset()
        self.config = model_config()

    def test_decomposition_reconstructs_input_and_preserves_shape(self):
        sequence = torch.arange(48, dtype=torch.float32).reshape(3, 8, 2)
        seasonal, trend = MovingAverageDecomposition(kernel_size=5)(sequence)
        self.assertEqual(seasonal.shape, sequence.shape)
        self.assertEqual(trend.shape, sequence.shape)
        torch.testing.assert_close(seasonal + trend, sequence, rtol=1e-6, atol=1e-6)

    def test_decomposition_rejects_even_kernel(self):
        with self.assertRaisesRegex(ValueError, "positive odd"):
            MovingAverageDecomposition(kernel_size=4)

    def test_forward_uses_x_seasonal_and_calendar(self):
        model = build_seeded_model(
            MatchedDLinearForecaster, self.config, seed=31, input_length=self.dataset.config.input_length, kernel_size=5
        )
        model.scaler.fit(self.dataset)
        batch = next(self.dataset.iter_batches("validation", batch_size=8))
        x = torch.as_tensor(batch.inputs.x, dtype=torch.float32)
        seasonal = torch.as_tensor(batch.inputs.seasonal, dtype=torch.float32)
        calendar = torch.as_tensor(batch.inputs.calendar, dtype=torch.float32)
        with torch.no_grad():
            for layer in list(model.seasonal_linear) + list(model.trend_linear):
                layer.weight.fill_(0.02)
                layer.bias.zero_()
            model.future_known_projection.weight.fill_(0.02)
            model.future_known_projection.bias.zero_()
            base = model(x, seasonal, calendar)
            changed_x = model(x + 0.25, seasonal, calendar)
            changed_seasonal = model(x, seasonal + 0.25, calendar)
            changed_calendar = model(x, seasonal, calendar + 0.25)
        self.assertEqual(base.shape, batch.target.shape)
        self.assertTrue(torch.isfinite(base).all())
        self.assertFalse(torch.allclose(base, changed_x))
        self.assertFalse(torch.allclose(base, changed_seasonal))
        self.assertFalse(torch.allclose(base, changed_calendar))

    def test_shared_channel_variant_and_shape_guards(self):
        model = MatchedDLinearForecaster(
            self.config, input_length=self.dataset.config.input_length, kernel_size=3, individual=False
        )
        model.scaler.fit(self.dataset)
        batch = next(self.dataset.iter_batches("validation", batch_size=4))
        x = torch.as_tensor(batch.inputs.x, dtype=torch.float32)
        seasonal = torch.as_tensor(batch.inputs.seasonal, dtype=torch.float32)
        calendar = torch.as_tensor(batch.inputs.calendar, dtype=torch.float32)
        prediction = model(x, seasonal, calendar)
        self.assertEqual(prediction.shape, batch.target.shape)
        with self.assertRaisesRegex(ValueError, "calendar shape"):
            model(x, seasonal, calendar[:, :, :2])


    def test_nlinear_zero_residual_weights_reduce_to_last_value(self):
        model = MatchedNLinearForecaster(
            self.config, input_length=self.dataset.config.input_length
        )
        model.scaler.fit(self.dataset)
        batch = next(self.dataset.iter_batches("validation", batch_size=8))
        x = torch.as_tensor(batch.inputs.x, dtype=torch.float32)
        seasonal = torch.as_tensor(batch.inputs.seasonal, dtype=torch.float32)
        calendar = torch.as_tensor(batch.inputs.calendar, dtype=torch.float32)
        with torch.no_grad():
            layers = list(model.linear) if isinstance(model.linear, nn.ModuleList) else [model.linear]
            for layer in layers:
                layer.weight.zero_()
                layer.bias.zero_()
            model.future_known_projection.weight.zero_()
            model.future_known_projection.bias.zero_()
            prediction = model(x, seasonal, calendar)
        expected = x[:, -1:, :].expand(-1, self.config.horizon, -1)
        torch.testing.assert_close(prediction, expected, rtol=0, atol=0)

    def test_nlinear_uses_x_seasonal_and_calendar(self):
        model = MatchedNLinearForecaster(
            self.config, input_length=self.dataset.config.input_length
        )
        model.scaler.fit(self.dataset)
        batch = next(self.dataset.iter_batches("validation", batch_size=8))
        x = torch.as_tensor(batch.inputs.x, dtype=torch.float32)
        seasonal = torch.as_tensor(batch.inputs.seasonal, dtype=torch.float32)
        calendar = torch.as_tensor(batch.inputs.calendar, dtype=torch.float32)
        with torch.no_grad():
            layers = list(model.linear) if isinstance(model.linear, nn.ModuleList) else [model.linear]
            for layer in layers:
                layer.weight.fill_(0.02)
                layer.bias.zero_()
            model.future_known_projection.weight.fill_(0.02)
            model.future_known_projection.bias.zero_()
            base = model(x, seasonal, calendar)
            changed_x = model(x + 0.25, seasonal, calendar)
            changed_seasonal = model(x, seasonal + 0.25, calendar)
            changed_calendar = model(x, seasonal, calendar + 0.25)
        self.assertEqual(base.shape, batch.target.shape)
        self.assertFalse(torch.allclose(base, changed_x))
        self.assertFalse(torch.allclose(base, changed_seasonal))
        self.assertFalse(torch.allclose(base, changed_calendar))

    def test_nlinear_training_updates_parameters(self):
        model = MatchedNLinearForecaster(
            self.config, input_length=self.dataset.config.input_length
        )
        before = [parameter.detach().clone() for parameter in model.parameters()]
        history = train_direct_mae(
            model, self.dataset, epochs=1, batch_size=32, seed=53
        )
        self.assertEqual(len(history), 1)
        self.assertTrue(np.isfinite(history[0]["mae"]))
        self.assertTrue(any(
            not torch.equal(old, new.detach())
            for old, new in zip(before, model.parameters())
        ))

    def test_training_changes_parameters_and_predicts_finite_values(self):
        model = build_seeded_model(
            MatchedDLinearForecaster, self.config, seed=41, input_length=self.dataset.config.input_length, kernel_size=5
        )
        before = [parameter.detach().clone() for parameter in model.parameters()]
        history = train_direct_mae(
            model, self.dataset, epochs=2, batch_size=32, seed=41
        )
        self.assertEqual(len(history), 2)
        self.assertTrue(all(np.isfinite(row["mae"]) for row in history))
        self.assertTrue(any(
            not torch.equal(old, new.detach())
            for old, new in zip(before, model.parameters())
        ))
        batch = next(self.dataset.iter_batches("validation", batch_size=8))
        with torch.no_grad():
            prediction = model(
                torch.as_tensor(batch.inputs.x, dtype=torch.float32),
                torch.as_tensor(batch.inputs.seasonal, dtype=torch.float32),
                torch.as_tensor(batch.inputs.calendar, dtype=torch.float32),
            )
        self.assertEqual(prediction.shape, batch.target.shape)
        self.assertTrue(torch.isfinite(prediction).all())


if __name__ == "__main__":
    unittest.main()
