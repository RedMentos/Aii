"""Synthetic tests for the raw-window controls."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta

import numpy as np

from v14.m1.array_data import ArrayDataset
from v14.m1.raw_probes import RawWindowMLP, RawWindowProbe
from v14.m1.data import DataConfig, MinuteRow


def rows_for(n: int):
    start = datetime(2020, 1, 1)
    return [
        MinuteRow(
            start + timedelta(minutes=i),
            (float((i % 17) / 17.0), float((i % 11) / 11.0)),
        )
        for i in range(n)
    ]


class RawWindowProbeTests(unittest.TestCase):
    def setUp(self):
        self.dataset = ArrayDataset(
            rows_for(1200),
            ("Global_active_power", "Voltage"),
            DataConfig(
                input_length=8, horizon=3, max_candidate_input_length=8,
                seasonal_lags=(3, 5), train_fraction=0.70, validation_fraction=0.15,
            ),
        )
        self.batch = next(self.dataset.iter_batches("validation", batch_size=16))

    def test_linear_raw_probe_fits_and_returns_finite_multi_horizon_output(self):
        model = RawWindowProbe(epochs=2, learning_rate=0.01, seed=7, batch_size=16).fit(self.dataset)
        prediction = model.predict(self.batch)
        self.assertEqual(prediction.shape, self.batch.target.shape)
        self.assertTrue(np.isfinite(prediction).all())
        self.assertGreater(model.parameter_count, 0)
        self.assertEqual(len(model.epoch_mae), 2)
        self.assertEqual(model.n_train_windows, sum(len(b.origin_indices) for b in self.dataset.iter_batches("train", batch_size=64)))

    def test_raw_mlp_is_nonlinear_and_has_more_parameters(self):
        linear = RawWindowProbe(epochs=1, seed=9, batch_size=16).fit(self.dataset)
        mlp = RawWindowMLP(hidden_width=12, epochs=1, seed=9, batch_size=16).fit(self.dataset)
        self.assertGreater(mlp.parameter_count, linear.parameter_count)
        self.assertEqual(mlp.predict(self.batch).shape, self.batch.target.shape)
        self.assertTrue(np.isfinite(mlp.predict(self.batch)).all())

    def test_seed_reproducibility(self):
        a = RawWindowProbe(epochs=1, seed=23, batch_size=32).fit(self.dataset)
        b = RawWindowProbe(epochs=1, seed=23, batch_size=32).fit(self.dataset)
        np.testing.assert_allclose(a.predict(self.batch), b.predict(self.batch), rtol=0, atol=0)

    def test_fit_never_reads_test_split(self):
        model = RawWindowProbe(epochs=1, batch_size=16)
        model.fit(self.dataset)
        with self.assertRaises(PermissionError):
            model.evaluate(self.dataset, "test")


if __name__ == "__main__":
    unittest.main()
