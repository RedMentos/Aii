"""Integration tests for the M1 validation-only experiment runner."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from experiments.m1.array_data import ArrayDataset
from experiments.m1.baselines import LADARBaseline, RidgeARBaseline
from experiments.m1.data import DataConfig, MinuteRow
from experiments.m1.raw_probes import RawWindowProbe
from experiments.m1.download_uci import DATASET_DOI, DATASET_LICENSE, EXPECTED_MEMBER
from experiments.m1.runner import (
    PilotConfig,
    TrainingWindowView,
    _load_download_manifest,
    run_validation_experiment,
)


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
    return ArrayDataset(rows, ("Global_active_power", "Voltage"), config)


class TrainingWindowViewTests(unittest.TestCase):
    def test_cap_applies_only_to_train_and_truncates_last_batch(self):
        dataset = synthetic_dataset()
        view = TrainingWindowView(dataset, 37)
        train_count = sum(
            len(batch.origin_indices)
            for batch in view.iter_batches("train", batch_size=16, shuffle=False)
        )
        full_train_count = sum(
            len(batch.origin_indices)
            for batch in dataset.iter_batches("train", batch_size=16, shuffle=False)
        )
        validation_count = sum(
            len(batch.origin_indices)
            for batch in view.iter_batches("validation", batch_size=16, shuffle=False)
        )
        full_validation_count = sum(
            len(batch.origin_indices)
            for batch in dataset.iter_batches("validation", batch_size=16, shuffle=False)
        )
        self.assertEqual(train_count, 37)
        self.assertGreater(full_train_count, train_count)
        self.assertEqual(validation_count, full_validation_count)
        batches = list(view.iter_batches("train", batch_size=16, shuffle=False))
        self.assertEqual([len(batch.origin_indices) for batch in batches], [16, 16, 5])


class ScalerCapParityTests(unittest.TestCase):
    def setUp(self):
        self.dataset = synthetic_dataset()
        self.view = TrainingWindowView(self.dataset, 37)
        self.full_train_windows = sum(
            len(batch.origin_indices)
            for batch in self.dataset.iter_batches("train", batch_size=16)
        )

    def test_raw_window_scaler_uses_all_train_windows_but_fit_obeys_cap(self):
        capped = RawWindowProbe(epochs=1, seed=13, batch_size=16).fit(self.view)
        full = RawWindowProbe(epochs=1, seed=13, batch_size=16).fit(self.dataset)
        self.assertEqual(capped.n_train_windows, 37)
        self.assertEqual(capped.n_scaler_windows, self.full_train_windows)
        self.assertEqual(full.n_scaler_windows, self.full_train_windows)
        np.testing.assert_array_equal(capped.feature_mean, full.feature_mean)
        np.testing.assert_array_equal(capped.feature_scale, full.feature_scale)

    def test_ar_scalers_use_all_train_windows_but_linear_fits_obey_cap(self):
        capped_ridge = RidgeARBaseline(ar_lags=(1, 4, 8)).fit(self.view, batch_size=16)
        full_ridge = RidgeARBaseline(ar_lags=(1, 4, 8)).fit(self.dataset, batch_size=16)
        self.assertEqual(capped_ridge.n_train_windows, 37)
        self.assertEqual(capped_ridge.n_scaler_windows, self.full_train_windows)
        np.testing.assert_array_equal(capped_ridge.feature_mean, full_ridge.feature_mean)
        np.testing.assert_array_equal(capped_ridge.feature_scale, full_ridge.feature_scale)

        capped_lad = LADARBaseline(ar_lags=(1, 4, 8), epochs=1, seed=13).fit(
            self.view, batch_size=16
        )
        self.assertEqual(capped_lad.n_train_windows, 37)
        self.assertEqual(capped_lad.n_scaler_windows, self.full_train_windows)
        np.testing.assert_array_equal(capped_lad.feature_mean, full_ridge.feature_mean)
        np.testing.assert_array_equal(capped_lad.feature_scale, full_ridge.feature_scale)


class PilotRunnerTests(unittest.TestCase):
    def test_runner_binds_optional_download_sidecar_to_exact_source_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / EXPECTED_MEMBER
            payload = b"UCI data bytes"
            source.write_bytes(payload)
            raw_hash = hashlib.sha256(payload).hexdigest()
            sidecar = source.with_name(source.name + ".provenance.json")
            manifest = {
                "schema": "m1.uci-download-provenance.v1",
                "doi": DATASET_DOI,
                "license": DATASET_LICENSE,
                "member_name": "folder/" + EXPECTED_MEMBER,
                "source_url": "https://archive.ics.uci.edu/static/public/235/data.zip",
                "file_sha256": raw_hash,
                "file_size_bytes": len(payload),
            }
            sidecar.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(_load_download_manifest(source, raw_hash), manifest)
            manifest["file_sha256"] = "0" * 64
            sidecar.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                _load_download_manifest(source, raw_hash)

    def test_all_model_families_run_on_same_validation_origins(self):
        dataset = synthetic_dataset()
        models = (
            "persistence",
            "seasonal_persistence_lag_0",
            "seasonal_persistence_lag_1",
            "train_mean",
            "train_median",
            "ridge_ar_l2",
            "lad_ar_l1_l2penalty",
            "raw_window_probe",
            "raw_window_mlp",
            "matched_dlinear",
            "matched_nlinear",
            "jepa_pretrain",
            "frozen_context_probe",
            "random_context_probe",
            "direct_mae",
            "raw_gru",
        )
        config = PilotConfig(
            input_length=8,
            horizon=4,
            max_candidate_input_length=8,
            seasonal_lags=(4, 8),
            validation_start=None,
            test_start=None,
            models=models,
            seeds=(23,),
            reference_model="persistence",
            batch_size=32,
            eval_batch_size=64,
            max_train_windows=96,
            epochs=1,
            patch_size=2,
            d_model=8,
            n_heads=2,
            encoder_layers=1,
            predictor_layers=1,
            ema_start=0.5,
            ema_end=0.9,
            dlinear_kernel_size=5,
            gru_hidden_size=12,
            ar_lags=(1, 4, 8),
            primary_start=2,
            primary_end=4,
            report_horizons=(1, 2, 4),
            bootstrap_block_len_minutes=1440,
            bootstrap_resamples=30,
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "validation.json"
            result, digest = run_validation_experiment(
                dataset, config, output_path=output
            )
            self.assertEqual(len(digest), 64)
            self.assertEqual(len(result["runs"]), len(models) - 1)
            self.assertFalse(result["experiment"]["test_split_accessed"])
            self.assertFalse(result["experiment"]["hyperparameters_locked"])
            self.assertEqual(result["paired_block_bootstrap"]["reference_model"], "persistence")
            self.assertEqual(
                {row["n_windows"] for row in result["runs"]},
                {result["data_provenance"]["validation"]["accepted_windows"]},
            )
            self.assertEqual(
                {row["model"] for row in result["runs"]},
                {name for name in models if name != "jepa_pretrain"},
            )
            manifest = result["training_manifest"]
            self.assertEqual(len(manifest), len(models))
            torch_entries = [row for row in manifest if row["checkpoint_sha256"]]
            self.assertGreaterEqual(len(torch_entries), 5)
            for row in torch_entries:
                self.assertEqual(len(row["checkpoint_sha256"]), 64)
                self.assertTrue(Path(row["checkpoint_path"]).is_file())
            persisted = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(persisted["experiment"]["code_commit"], result["experiment"]["code_commit"])
            self.assertEqual(persisted["data_provenance"]["parsed_dataset_sha256"], dataset.dataset_sha256)

    def test_runner_rejects_dataset_config_drift(self):
        dataset = synthetic_dataset()
        config = PilotConfig(
            input_length=8,
            horizon=4,
            max_candidate_input_length=8,
            seasonal_lags=(4, 8),
            validation_start=None,
            test_start=None,
            models=("persistence",),
            seeds=(1,),
            primary_start=2,
            primary_end=4,
            report_horizons=(1, 2, 4),
        )
        mismatched = PilotConfig(
            input_length=8,
            horizon=4,
            max_candidate_input_length=9,
            seasonal_lags=(4, 8),
            validation_start=None,
            test_start=None,
            models=("persistence",),
            seeds=(1,),
            primary_start=2,
            primary_end=4,
            report_horizons=(1, 2, 4),
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "config"):
                run_validation_experiment(
                    dataset, mismatched, output_path=Path(directory) / "never.json"
                )


if __name__ == "__main__":
    unittest.main()
