"""Synthetic end-to-end validation of the M1 model and metric interfaces."""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from experiments.m1.array_data import ArrayDataset
from experiments.m1.baselines import PersistenceBaseline
from experiments.m1.data import DataConfig, MinuteRow
from experiments.m1.dlinear import MatchedDLinearForecaster, MatchedNLinearForecaster
from experiments.m1.gru import RawGRUForecaster
from experiments.m1.jepa import (
    DirectMAEForecaster,
    FrozenContextProbe,
    JEPAConfig,
    JEPAForecaster,
    make_random_context_probe,
)
from experiments.m1.metrics import evaluate_suite, write_result_atomic
from experiments.m1.training import (
    TorchBatchPredictor,
    build_seeded_model,
    current_git_commit,
    evaluate_jepa,
    train_direct_mae,
    train_frozen_probe,
    train_jepa,
    train_raw_gru,
)


def synthetic_dataset():
    start = datetime(2021, 1, 1)
    rows = []
    for i in range(1600):
        daily = np.sin(2 * np.pi * (i % 1440) / 1440)
        weekly = np.cos(2 * np.pi * (i % 10080) / 10080)
        rows.append(MinuteRow(
            start + timedelta(minutes=i),
            (float(1.5 + 0.4 * daily + 0.05 * np.sin(i / 13)),
             float(220.0 + 3.0 * weekly + 0.2 * np.cos(i / 17))),
        ))
    config = DataConfig(
        input_length=8, horizon=4, max_candidate_input_length=8,
        seasonal_lags=(4, 8), train_fraction=0.70, validation_fraction=0.15,
    )
    return ArrayDataset(rows, ("Global_active_power", "Voltage"), config)


class EndToEndTests(unittest.TestCase):
    def test_synthetic_m1_validation_suite(self):
        dataset = synthetic_dataset()
        config = JEPAConfig(
            input_channels=2, seasonal_lags=2, horizon=4,
            calendar_features=4, patch_size=2, d_model=8,
            n_heads=2, encoder_layers=1, predictor_layers=1,
            dropout=0.0, ema_start=0.5, ema_end=0.9,
        )
        seed = 23
        jepa = build_seeded_model(JEPAForecaster, config, seed)
        jepa_history = train_jepa(jepa, dataset, epochs=1, batch_size=32, seed=seed)
        self.assertTrue(np.isfinite(jepa_history[0]["latent_mse"]))
        validation = evaluate_jepa(jepa, dataset, batch_size=64)
        self.assertGreater(validation["n_windows"], 0)

        frozen = FrozenContextProbe(jepa, config, readout_seed=seed)
        frozen_history = train_frozen_probe(frozen, dataset, epochs=1, batch_size=32, seed=seed)
        self.assertTrue(np.isfinite(frozen_history[0]["mae"]))

        random_probe = make_random_context_probe(config, seed)
        random_history = train_frozen_probe(
            random_probe, dataset, epochs=1, batch_size=32, seed=seed
        )
        self.assertTrue(np.isfinite(random_history[0]["mae"]))

        direct = build_seeded_model(DirectMAEForecaster, config, seed)
        direct_history = train_direct_mae(
            direct, dataset, epochs=1, batch_size=32, seed=seed
        )
        self.assertTrue(np.isfinite(direct_history[0]["mae"]))

        dlinear = build_seeded_model(MatchedDLinearForecaster, config, seed, input_length=dataset.config.input_length, kernel_size=5)
        dlinear_history = train_direct_mae(
            dlinear, dataset, epochs=1, batch_size=32, seed=seed
        )
        self.assertTrue(np.isfinite(dlinear_history[0]["mae"]))

        nlinear = build_seeded_model(
            MatchedNLinearForecaster, config, seed,
            input_length=dataset.config.input_length,
        )
        nlinear_history = train_direct_mae(
            nlinear, dataset, epochs=1, batch_size=32, seed=seed
        )
        self.assertTrue(np.isfinite(nlinear_history[0]["mae"]))

        raw_gru = build_seeded_model(RawGRUForecaster, config, seed, hidden_size=12)
        gru_history = train_raw_gru(raw_gru, dataset, epochs=1, batch_size=32, seed=seed)
        self.assertTrue(np.isfinite(gru_history[0]["mae"]))

        runs = [
            (PersistenceBaseline(), seed),
            (TorchBatchPredictor(direct, name="direct_mae"), seed),
            (TorchBatchPredictor(frozen, name="frozen_jepa_probe"), seed),
            (TorchBatchPredictor(random_probe, name="random_context_probe"), seed),
            (TorchBatchPredictor(raw_gru, name="raw_gru"), seed),
            (TorchBatchPredictor(dlinear, name="matched_dlinear"), seed),
            (TorchBatchPredictor(nlinear, name="matched_nlinear"), seed),
        ]
        result = evaluate_suite(
            runs, dataset, reference_model="persistence",
            code_commit=current_git_commit(Path(__file__).resolve().parents[2]),
            primary_start=2, primary_end=4, report_horizons=(1, 2, 4),
            block_len_minutes=1440, n_resamples=50, batch_size=64,
        )
        self.assertEqual(len(result["runs"]), 7)
        self.assertIn("delta_ci", result["paired_block_bootstrap"]["models"]["direct_mae"])
        self.assertIn("delta_ci", result["paired_block_bootstrap"]["models"]["matched_dlinear"])
        self.assertIn("delta_ci", result["paired_block_bootstrap"]["models"]["matched_nlinear"])
        with tempfile.TemporaryDirectory() as directory:
            digest = write_result_atomic(result, Path(directory) / "m1-validation.json")
            self.assertEqual(len(digest), 64)


if __name__ == "__main__":
    unittest.main()
