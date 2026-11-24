"""CPU smoke/regression tests for the clean-room JEPA and direct-MAE models."""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import torch

from experiments.m1.array_data import ArrayDataset
from experiments.m1.data import DataConfig, MinuteRow
from experiments.m1.jepa import (
    DirectMAEForecaster,
    FrozenLatentProbe,
    JEPAConfig,
    JEPAForecaster,
    collapse_metrics,
    jepa_loss,
    patchify,
    trainable_parameter_count,
    total_parameter_count,
)
from experiments.m1.training import (
    load_checkpoint,
    save_checkpoint_atomic,
    train_direct_mae,
    train_frozen_probe,
    train_jepa,
)


def fixture_dataset():
    start = datetime(2020, 1, 1)
    rows = [
        MinuteRow(
            start + timedelta(minutes=i),
            (float((i % 13) / 13.0), float((i % 7) / 7.0)),
        )
        for i in range(1200)
    ]
    config = DataConfig(
        input_length=8, horizon=4, max_candidate_input_length=8,
        seasonal_lags=(4, 8), train_fraction=0.70, validation_fraction=0.15,
    )
    return ArrayDataset(rows, ("Global_active_power", "Voltage"), config)


def model_config():
    return JEPAConfig(
        input_channels=2, seasonal_lags=2, horizon=4, calendar_features=4,
        patch_size=2, d_model=8, n_heads=2, encoder_layers=1,
        predictor_layers=1, dropout=0.0, ema_start=0.5, ema_end=0.9,
    )


class JEPAModelTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(3)
        self.dataset = fixture_dataset()
        self.config = model_config()

    def test_patchify_and_unpatch_padding(self):
        x = torch.arange(15, dtype=torch.float32).reshape(1, 5, 3)
        patches, original_length = patchify(x, 2)
        self.assertEqual(patches.shape, (1, 3, 6))
        self.assertEqual(original_length, 5)

    def test_predictor_output_does_not_depend_on_future_target(self):
        model = JEPAForecaster(self.config).eval()
        batch = next(self.dataset.iter_batches("validation", batch_size=8))
        x = torch.as_tensor(batch.inputs.x)
        s = torch.as_tensor(batch.inputs.seasonal)
        cal = torch.as_tensor(batch.inputs.calendar)
        y1 = torch.as_tensor(batch.target)
        y2 = y1 + 1000.0
        pred1, _ = model.predict_latents(x, s, cal)
        pred2, _ = model.predict_latents(x, s, cal)
        torch.testing.assert_close(pred1, pred2, rtol=0, atol=0)
        out1 = model.forward_pretrain(x, s, cal, y1)
        out2 = model.forward_pretrain(x, s, cal, y2)
        torch.testing.assert_close(out1["prediction"], out2["prediction"], rtol=0, atol=0)
        self.assertFalse(torch.equal(out1["target"], out2["target"]))

    def test_jepa_loss_and_collapse_telemetry_are_finite(self):
        model = JEPAForecaster(self.config)
        batch = next(self.dataset.iter_batches("train", batch_size=8))
        tensors = [torch.as_tensor(v, dtype=torch.float32) for v in (
            batch.inputs.x, batch.inputs.seasonal, batch.inputs.calendar, batch.target
        )]
        outputs = model.forward_pretrain(*tensors)
        loss, parts = jepa_loss(outputs, self.config)
        self.assertTrue(torch.isfinite(loss))
        self.assertTrue(all(torch.isfinite(value) for value in parts.values()))
        stats = collapse_metrics(outputs["context"])
        self.assertTrue(np.isfinite(list(stats.values())).all())
        self.assertGreaterEqual(stats["effective_rank"], 0.0)

    def test_ema_update_moves_target_toward_online(self):
        model = JEPAForecaster(self.config)
        target = next(model.target_encoder.parameters())
        online = next(model.context_encoder.parameters())
        before = target.detach().clone()
        with torch.no_grad():
            online.add_(1.0)
        tau = model.update_target_encoder(step=0, total_steps=10)
        self.assertAlmostEqual(tau, self.config.ema_start)
        expected = before * tau + online.detach() * (1.0 - tau)
        torch.testing.assert_close(target, expected)

    def test_jepa_training_and_checkpoint_reload(self):
        model = JEPAForecaster(self.config)
        initial = next(model.context_encoder.parameters()).detach().clone()
        history = train_jepa(
            model, self.dataset, epochs=2, batch_size=32,
            learning_rate=1e-3, seed=5,
        )
        self.assertEqual(len(history), 2)
        self.assertTrue(all(np.isfinite(row["total"]) for row in history))
        self.assertFalse(torch.equal(initial, next(model.context_encoder.parameters()).detach()))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jepa.pt"
            digest = save_checkpoint_atomic(
                model, self.config, path, code_commit="a" * 40,
                metadata={"epoch": 2},
            )
            self.assertEqual(len(digest), 64)
            restored = JEPAForecaster(self.config)
            metadata = load_checkpoint(
                restored, self.config, path, expected_code_commit="a" * 40
            )
            self.assertEqual(metadata, {"epoch": 2})
            batch = next(self.dataset.iter_batches("validation", batch_size=8))
            x = torch.as_tensor(batch.inputs.x)
            s = torch.as_tensor(batch.inputs.seasonal)
            cal = torch.as_tensor(batch.inputs.calendar)
            torch.testing.assert_close(
                model.predict_latents(x, s, cal)[0],
                restored.predict_latents(x, s, cal)[0],
            )

    def test_frozen_and_random_encoder_probes_train_only_linear_readout(self):
        backbone = JEPAForecaster(self.config)
        probe = FrozenLatentProbe(backbone, self.config)
        frozen_before = [p.detach().clone() for p in probe.backbone.parameters()]
        readout_before = probe.value_head.weight.detach().clone()
        history = train_frozen_probe(
            probe, self.dataset, epochs=1, batch_size=32, seed=12
        )
        self.assertTrue(np.isfinite(history[0]["mae"]))
        self.assertFalse(torch.equal(readout_before, probe.value_head.weight.detach()))
        for before, after in zip(frozen_before, probe.backbone.parameters()):
            torch.testing.assert_close(before, after)
        self.assertTrue(all(not p.requires_grad for p in probe.backbone.parameters()))

    def test_checkpoint_rejects_code_commit_drift(self):
        model = JEPAForecaster(self.config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.pt"
            save_checkpoint_atomic(model, self.config, path, code_commit="a" * 40)
            with self.assertRaisesRegex(ValueError, "code_commit"):
                load_checkpoint(
                    JEPAForecaster(self.config), self.config, path,
                    expected_code_commit="b" * 40,
                )

    def test_direct_mae_training_and_forecast_shape(self):
        model = DirectMAEForecaster(self.config)
        history = train_direct_mae(
            model, self.dataset, epochs=2, batch_size=32,
            learning_rate=1e-3, seed=9,
        )
        self.assertEqual(len(history), 2)
        self.assertTrue(all(np.isfinite(row["mae"]) for row in history))
        self.assertGreater(trainable_parameter_count(model), 0)
        self.assertEqual(total_parameter_count(model), trainable_parameter_count(model))
        self.assertTrue(np.isfinite(
            __import__("experiments.m1.training", fromlist=["evaluate_direct_mae"])
            .evaluate_direct_mae(model, self.dataset, batch_size=64)
        ))


if __name__ == "__main__":
    unittest.main()
