"""M1b shared-weight recurrence model and runner tests."""
from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import torch

from experiments.m1.data import DataConfig, MinuteRow
from experiments.m1.jepa import (
    JEPAConfig,
    RecurrentDirectMAEForecaster,
    RecurrentJEPAForecaster,
    make_random_recurrent_context_probe,
    total_parameter_count,
    trainable_parameter_count,
)
from experiments.m1.recurrence import run_recurrence_ablation
from experiments.m1.runner import PilotConfig
from experiments.m1.training import train_direct_mae, train_jepa


def synthetic_dataset():
    start = datetime(2021, 1, 1)
    rows = []
    for i in range(1600):
        daily = np.sin(2.0 * np.pi * (i % 1440) / 1440.0)
        weekly = np.cos(2.0 * np.pi * (i % 10080) / 10080.0)
        rows.append(MinuteRow(
            start + timedelta(minutes=i),
            (
                float(1.5 + 0.4 * daily + 0.05 * np.sin(i / 13.0)),
                float(220.0 + 3.0 * weekly + 0.2 * np.cos(i / 17.0)),
            ),
        ))
    config = DataConfig(
        input_length=8,
        horizon=4,
        max_candidate_input_length=8,
        seasonal_lags=(4, 8),
        train_fraction=0.70,
        validation_fraction=0.15,
    )
    from experiments.m1.array_data import ArrayDataset
    return ArrayDataset(rows, ("Global_active_power", "Voltage"), config)


def model_config(recurrent_steps=1):
    return JEPAConfig(
        input_channels=2,
        seasonal_lags=2,
        horizon=4,
        patch_size=2,
        d_model=8,
        n_heads=2,
        encoder_layers=1,
        recurrent_steps=recurrent_steps,
        predictor_layers=1,
        ema_start=0.5,
        ema_end=0.9,
    )


class SharedRecurrenceModelTests(unittest.TestCase):
    def test_parameter_count_is_constant_for_t1_t2_t4(self):
        jepa_models = [
            RecurrentJEPAForecaster(model_config(step))
            for step in (1, 2, 4)
        ]
        direct_models = [
            RecurrentDirectMAEForecaster(model_config(step))
            for step in (1, 2, 4)
        ]
        self.assertEqual(
            len({trainable_parameter_count(model) for model in jepa_models}), 1
        )
        self.assertEqual(
            len({total_parameter_count(model) for model in jepa_models}), 1
        )
        self.assertEqual(
            len({trainable_parameter_count(model) for model in direct_models}), 1
        )
        self.assertEqual(
            len({total_parameter_count(model) for model in direct_models}), 1
        )

    def test_recurrence_depth_changes_representation_without_changing_shape(self):
        torch.manual_seed(23)
        x = torch.randn(3, 8, 2)
        outputs = []
        base = RecurrentJEPAForecaster(model_config(1))
        base.eval()
        for step in (1, 2, 4):
            model = RecurrentJEPAForecaster(model_config(step))
            model.load_state_dict(base.state_dict(), strict=True)
            model.eval()
            with torch.no_grad():
                outputs.append(model.context_encoder(x))
        self.assertEqual(tuple(outputs[0].shape), (3, 4, 8))
        self.assertEqual(tuple(outputs[1].shape), tuple(outputs[0].shape))
        self.assertEqual(tuple(outputs[2].shape), tuple(outputs[0].shape))
        self.assertFalse(torch.allclose(outputs[0], outputs[1]))
        self.assertFalse(torch.allclose(outputs[1], outputs[2]))

    def test_recurrent_jepa_updates_online_and_ema_target_weights(self):
        dataset = synthetic_dataset()
        model = RecurrentJEPAForecaster(model_config(2))
        online_before = [p.detach().clone() for p in model.context_encoder.parameters()]
        target_before = [p.detach().clone() for p in model.target_encoder.parameters()]
        history = train_jepa(
            model, dataset, epochs=1, batch_size=32, learning_rate=1e-3, seed=23
        )
        online_after = list(model.context_encoder.parameters())
        target_after = list(model.target_encoder.parameters())
        self.assertTrue(any(not torch.equal(a, b) for a, b in zip(online_before, online_after)))
        self.assertTrue(any(not torch.equal(a, b) for a, b in zip(target_before, target_after)))
        self.assertTrue(all(p.grad is None for p in model.target_encoder.parameters()))
        self.assertTrue(np.isfinite([row["total"] for row in history]).all())

    def test_recurrent_direct_mae_updates_numeric_parameters(self):
        dataset = synthetic_dataset()
        model = RecurrentDirectMAEForecaster(model_config(4))
        before = [p.detach().clone() for p in model.parameters()]
        history = train_direct_mae(
            model, dataset, epochs=1, batch_size=32, learning_rate=1e-3, seed=23
        )
        self.assertTrue(any(not torch.equal(a, b) for a, b in zip(before, model.parameters())))
        self.assertTrue(np.isfinite([row["mae"] for row in history]).all())

    def test_random_probe_uses_same_recurrent_encoder_contract(self):
        probe = make_random_recurrent_context_probe(model_config(4), seed=23)
        self.assertEqual(probe.encoder.recurrent_steps, 4)
        self.assertTrue(all(not p.requires_grad for p in probe.encoder.parameters()))


class RecurrenceRunnerTests(unittest.TestCase):
    def test_t1_t2_t4_end_to_end_synthetic_validation_only(self):
        dataset = synthetic_dataset()
        config = PilotConfig(
            input_length=8,
            horizon=4,
            max_candidate_input_length=8,
            seasonal_lags=(4, 8),
            validation_start=None,
            test_start=None,
            models=("persistence",),
            seeds=(23,),
            reference_model="persistence",
            batch_size=16,
            eval_batch_size=32,
            max_train_windows=32,
            epochs=1,
            learning_rate=1e-3,
            patch_size=2,
            d_model=8,
            n_heads=2,
            encoder_layers=2,
            predictor_layers=1,
            ema_start=0.5,
            ema_end=0.9,
            dlinear_kernel_size=5,
            gru_hidden_size=12,
            raw_mlp_hidden_size=8,
            ar_lags=(1, 4, 8),
            primary_start=2,
            primary_end=4,
            report_horizons=(1, 2, 4),
            bootstrap_block_len_minutes=120,
            bootstrap_resamples=20,
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "m1b.json"
            result, digest = run_recurrence_ablation(
                dataset, config, output_path=output, steps=(1, 2, 4)
            )
            self.assertEqual(len(digest), 64)
            self.assertFalse(result["experiment"]["test_split_accessed"])
            self.assertEqual(result["experiment"]["recurrence_steps"], [1, 2, 4])
            self.assertEqual(len(result["training_manifest"]), 12)
            self.assertEqual(len(result["runs"]), 10)
            self.assertEqual(
                {row["n_windows"] for row in result["runs"]},
                {result["data_provenance"]["validation"]["accepted_windows"]},
            )
            self.assertEqual(
                {row["model"] for row in result["runs"]},
                {
                    "persistence",
                    "jepa_frozen_probe_t1", "jepa_frozen_probe_t2", "jepa_frozen_probe_t4",
                    "random_recurrent_probe_t1", "random_recurrent_probe_t2", "random_recurrent_probe_t4",
                    "recurrent_direct_mae_t1", "recurrent_direct_mae_t2", "recurrent_direct_mae_t4",
                },
            )
            for role in (
                "jepa_pretrain_t",
                "jepa_frozen_probe_t",
                "random_recurrent_probe_t",
                "recurrent_direct_mae_t",
            ):
                rows = [
                    row for row in result["training_manifest"]
                    if row["model"].startswith(role)
                ]
                self.assertEqual(len({row["shared_block_parameter_count"] for row in rows}), 1)
                self.assertEqual(len({row["total_parameter_count"] for row in rows}), 1)
                for row in rows:
                    self.assertEqual(row["train_windows_per_epoch"], 32)
                    expected_multiplier = 2 if row["model"].startswith("jepa_pretrain_t") else 1
                    self.assertEqual(
                        row["encoder_block_calls_per_epoch"],
                        expected_multiplier * 2 * row["recurrent_steps"],
                    )
                    self.assertEqual(
                        row["encoder_block_calls_total"],
                        row["encoder_block_calls_per_epoch"],
                    )
                    self.assertEqual(len(row["checkpoint_sha256"]), 64)
                    self.assertTrue(Path(row["checkpoint_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
