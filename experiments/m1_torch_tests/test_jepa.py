"""CPU smoke/regression tests for the clean-room JEPA and direct-MAE models."""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
import re
import subprocess

import numpy as np
import torch

from experiments.m1.array_data import ArrayDataset
from experiments.m1.data import DataConfig, MinuteRow
from experiments.m1.gru import RawGRUForecaster
from experiments.m1.jepa import (
    DirectMAEForecaster,
    FrozenContextProbe,
    make_random_context_probe,
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
    train_raw_gru,
    evaluate_jepa,
    TorchBatchPredictor,
    build_seeded_model,
    current_git_commit,
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

    def test_current_git_commit_resolves_exact_head(self):
        repo_root = Path(__file__).resolve().parents[2]
        commit = current_git_commit(repo_root)
        self.assertRegex(commit, r"^[0-9a-f]{40}$")

    def test_current_git_commit_rejects_dirty_worktree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "m1-test@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "M1 Test"], cwd=root, check=True)
            (root / "tracked.txt").write_text("locked", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "test"], cwd=root, check=True, capture_output=True)
            self.assertRegex(current_git_commit(root), r"^[0-9a-f]{40}$")
            (root / "untracked.py").write_text("print('dirty')", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "clean working tree"):
                current_git_commit(root)

    def test_seeded_model_factory_controls_initial_weights(self):
        first = build_seeded_model(JEPAForecaster, self.config, seed=71)
        second = build_seeded_model(JEPAForecaster, self.config, seed=71)
        third = build_seeded_model(JEPAForecaster, self.config, seed=72)
        for left, right in zip(first.context_encoder.parameters(), second.context_encoder.parameters()):
            torch.testing.assert_close(left, right, rtol=0, atol=0)
        self.assertFalse(torch.equal(
            next(first.context_encoder.parameters()),
            next(third.context_encoder.parameters()),
        ))

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

    def test_channel_standardizer_uses_train_rows_only(self):
        model = JEPAForecaster(self.config)
        model.scaler.fit(self.dataset)
        start, end = self.dataset.bounds["train"]
        expected_mean = np.nanmean(self.dataset.train_values(), axis=0)
        expected_scale = np.nanstd(self.dataset.train_values(), axis=0)
        expected_scale[expected_scale <= 1e-6] = 1.0
        np.testing.assert_allclose(model.scaler.mean.cpu().numpy(), expected_mean, rtol=1e-6)
        np.testing.assert_allclose(model.scaler.scale.cpu().numpy(), expected_scale, rtol=1e-5, atol=1e-6)
        self.assertTrue(bool(model.scaler.fitted))

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
        self.assertAlmostEqual(history[-1]["ema_tau"], self.config.ema_end)
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

    def test_frozen_context_probe_uses_known_covariates_and_freezes_encoder(self):
        backbone = JEPAForecaster(self.config)
        probe = FrozenContextProbe(backbone, self.config)
        frozen_before = [p.detach().clone() for p in probe.encoder.parameters()]
        readout_before = probe.readout.weight.detach().clone()
        history = train_frozen_probe(
            probe, self.dataset, epochs=1, batch_size=32, seed=19
        )
        self.assertTrue(np.isfinite(history[0]["mae"]))
        self.assertFalse(torch.equal(readout_before, probe.readout.weight.detach()))
        for before, after in zip(frozen_before, probe.encoder.parameters()):
            torch.testing.assert_close(before, after)
        batch = next(self.dataset.iter_batches("validation", batch_size=8))
        prediction = probe(
            torch.as_tensor(batch.inputs.x),
            torch.as_tensor(batch.inputs.seasonal),
            torch.as_tensor(batch.inputs.calendar),
        )
        self.assertEqual(prediction.shape, batch.target.shape)

    def test_random_context_probe_is_seed_reproducible(self):
        first = make_random_context_probe(self.config, seed=42)
        second = make_random_context_probe(self.config, seed=42)
        third = make_random_context_probe(self.config, seed=43)
        for left, right in zip(first.encoder.parameters(), second.encoder.parameters()):
            torch.testing.assert_close(left, right, rtol=0, atol=0)
        torch.testing.assert_close(first.readout.weight, second.readout.weight, rtol=0, atol=0)
        self.assertFalse(torch.equal(
            next(first.encoder.parameters()), next(third.encoder.parameters())
        ))

    def test_streaming_validation_collapse_telemetry(self):
        model = JEPAForecaster(self.config)
        model.scaler.fit(self.dataset)
        result = evaluate_jepa(model, self.dataset, batch_size=64)
        self.assertGreater(result["n_windows"], 0)
        self.assertTrue(np.isfinite(result["latent_mse"]))
        self.assertGreaterEqual(result["context_collapse"]["effective_rank"], 0.0)
        self.assertGreaterEqual(result["target_collapse"]["effective_rank"], 0.0)

    def test_torch_batch_adapter_returns_numpy_forecasts(self):
        model = DirectMAEForecaster(self.config)
        model.scaler.fit(self.dataset)
        predictor = TorchBatchPredictor(model, name="direct_mae")
        batch = next(self.dataset.iter_batches("validation", batch_size=8))
        prediction = predictor.predict(batch)
        self.assertEqual(prediction.shape, batch.target.shape)
        self.assertTrue(np.isfinite(prediction).all())

    def test_raw_gru_uses_common_inputs_and_trains(self):
        model = RawGRUForecaster(self.config, hidden_size=12, num_layers=1)
        history = train_raw_gru(
            model, self.dataset, epochs=1, batch_size=32, seed=27
        )
        self.assertTrue(np.isfinite(history[0]["mae"]))
        batch = next(self.dataset.iter_batches("validation", batch_size=8))
        prediction = model(
            torch.as_tensor(batch.inputs.x),
            torch.as_tensor(batch.inputs.seasonal),
            torch.as_tensor(batch.inputs.calendar),
        )
        self.assertEqual(prediction.shape, batch.target.shape)

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
