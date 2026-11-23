"""Bounded-memory array-window tests for V14 M1."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest

import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

from v14.m1.array_data import ArrayDataset
from v14.m1.data import (
    DataConfig,
    MinuteRow,
    build_chronological_boundaries,
    data_config_sha256,
    dataset_sha256,
    parse_uci,
    make_split,
    split_boundaries_sha256,
)


def rows_for(n: int, missing=()):
    start = datetime(2020, 1, 1)
    missing = set(missing)
    return [
        MinuteRow(
            start + timedelta(minutes=i),
            (None if i in missing else float(i), float(i * 2)),
        )
        for i in range(n)
    ]


class DirectUCIArrayTests(unittest.TestCase):
    def _write_uci(self, path: Path, *, bad_value: str | None = None, bad_second: str | None = None):
        start = datetime(2020, 1, 1)
        lines = ["Date;Time;Global_active_power;Voltage"]
        for i in range(1000):
            stamp = start + timedelta(minutes=i)
            power = f"{i / 10:.1f}".replace(".", ",")
            if i == 12:
                power = "?"
            if i == 30 and bad_value is not None:
                power = bad_value
            time_text = stamp.strftime("%H:%M:%S")
            if i == 40 and bad_second is not None:
                time_text = bad_second
            voltage = f"{230 + i / 100:.2f}".replace(".", ",")
            lines.append(f"{stamp.strftime('%d/%m/%Y')};{time_text};{power};{voltage}")
        path.write_text("\\n".join(lines) + "\\n", encoding="utf-8")

    def test_two_pass_array_loader_matches_reference_parsed_data_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "uci.txt"
            self._write_uci(path)
            channels, rows = parse_uci(path)
            config = DataConfig(
                input_length=5, horizon=2, max_candidate_input_length=5,
                seasonal_lags=(2, 4), train_fraction=0.70, validation_fraction=0.15,
            )
            dataset = ArrayDataset.from_uci(path, config)
            self.assertEqual(dataset.channels, channels)
            self.assertEqual(dataset.dataset_sha256, dataset_sha256(rows, channels))
            self.assertEqual(dataset.values.shape, (1000, 2))
            self.assertTrue(np.isnan(dataset.values[12, 0]))
            batch = next(dataset.iter_batches("train", batch_size=16))
            self.assertEqual(batch.inputs.x.shape, (16, 5, 2))

    def test_two_pass_array_loader_rejects_nonfinite_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "uci.txt"
            self._write_uci(path, bad_value="inf")
            config = DataConfig(
                input_length=5, horizon=2, max_candidate_input_length=5,
                seasonal_lags=(2, 4), train_fraction=0.70, validation_fraction=0.15,
            )
            with self.assertRaisesRegex(ValueError, "non-finite"):
                ArrayDataset.from_uci(path, config)

    def test_two_pass_array_loader_rejects_truncated_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "uci.txt"
            path.write_text(
                "Date;Time;Global_active_power;Voltage\\n"
                "01/01/2020;00:00:00;1,0\\n",
                encoding="utf-8",
            )
            config = DataConfig(
                input_length=5, horizon=2, max_candidate_input_length=5,
                seasonal_lags=(2, 4), train_fraction=0.70, validation_fraction=0.15,
            )
            with self.assertRaisesRegex(ValueError, "truncated"):
                ArrayDataset.from_uci(path, config)

    def test_two_pass_array_loader_rejects_off_grid_timestamps(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "uci.txt"
            self._write_uci(path, bad_second="00:40:30")
            config = DataConfig(
                input_length=5, horizon=2, max_candidate_input_length=5,
                seasonal_lags=(2, 4), train_fraction=0.70, validation_fraction=0.15,
            )
            with self.assertRaisesRegex(ValueError, "whole minute"):
                ArrayDataset.from_uci(path, config)


class ArrayWindowTests(unittest.TestCase):
    def setUp(self):
        self.rows = rows_for(1000)
        self.channels = ("Global_active_power", "Voltage")
        self.config = DataConfig(
            input_length=5, horizon=2, max_candidate_input_length=5,
            seasonal_lags=(2, 4), train_fraction=0.70, validation_fraction=0.15,
        )
        self.dataset = ArrayDataset(self.rows, self.channels, self.config)

    def test_batch_shapes_and_common_input_bundle(self):
        batch = next(self.dataset.iter_batches("train", batch_size=32))
        self.assertEqual(batch.inputs.x.shape, (32, 5, 2))
        self.assertEqual(batch.inputs.seasonal.shape, (32, 2, 2, 2))
        self.assertEqual(batch.inputs.calendar.shape, (32, 2, 4))
        self.assertEqual(batch.target.shape, (32, 2, 2))
        self.assertEqual(batch.inputs.flatten().shape, (32, self.dataset.input_width))
        self.assertEqual(batch.origin_indices[0], 4)
        self.assertEqual(batch.inputs.x[0, :, 0].tolist(), [0, 1, 2, 3, 4])
        self.assertEqual(batch.target[0, :, 0].tolist(), [5, 6])
        self.assertEqual(batch.inputs.seasonal[0, 0, :, 0].tolist(), [3, 1])

    def test_calendar_ablation_has_zero_width_calendar_tensor(self):
        config = DataConfig(
            input_length=5, horizon=2, max_candidate_input_length=5,
            seasonal_lags=(2, 4), include_calendar=False,
            train_fraction=0.70, validation_fraction=0.15,
        )
        dataset = ArrayDataset(self.rows, self.channels, config)
        batch = next(dataset.iter_batches("train", batch_size=8))
        self.assertEqual(batch.inputs.calendar.shape, (8, 2, 0))
        self.assertEqual(batch.inputs.flatten().shape[1], 5 * 2 + 2 * 2 * 2)

    def test_lazy_stats_match_reference_list_builder(self):
        bounds = build_chronological_boundaries(len(self.rows), self.config)
        _, expected = make_split(
            self.rows, self.channels, self.config, "train", bounds["train"]
        )
        actual = self.dataset.split_stats("train", batch_size=37)
        self.assertEqual(actual.candidate_windows, expected.candidate_windows)
        self.assertEqual(actual.accepted_windows, expected.accepted_windows)
        self.assertEqual(actual.rejected_windows, expected.rejected_windows)
        self.assertEqual(actual.accepted_by_month, expected.accepted_by_month)
        self.assertEqual(actual.rejected_by_month, expected.rejected_by_month)

    def test_missing_seasonal_source_is_rejected_without_materializing_windows(self):
        config = DataConfig(
            input_length=5, horizon=2, max_candidate_input_length=5,
            seasonal_lags=(50,), train_fraction=0.70, validation_fraction=0.15,
        )
        dataset = ArrayDataset(rows_for(1000, {51}), self.channels, config)
        origins = [
            int(origin)
            for batch in dataset.iter_batches("train", batch_size=64)
            for origin in batch.origin_indices
        ]
        self.assertNotIn(100, origins)

    def test_hard_memory_budget_rejects_oversized_window_batch(self):
        config = DataConfig(
            input_length=5000, horizon=2, max_candidate_input_length=5000,
            seasonal_lags=(2, 4), train_fraction=0.40, validation_fraction=0.30,
        )
        dataset = ArrayDataset(rows_for(20000), self.channels, config)
        with self.assertRaisesRegex(ValueError, "window batch would require"):
            next(dataset.iter_batches("train", batch_size=8192))

    def test_batch_size_is_hard_bounded(self):
        with self.assertRaises(ValueError):
            list(self.dataset.iter_batches("train", batch_size=8193))
        for batch in self.dataset.iter_batches("train", batch_size=17):
            self.assertLessEqual(len(batch.origin_indices), 17)

    def test_test_split_requires_exact_hash_bound_preregistration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(PermissionError):
                next(self.dataset.iter_batches("test", batch_size=8))
            prereg = {
                "data_config_sha256": data_config_sha256(self.config),
                "split_boundaries_sha256": split_boundaries_sha256(self.rows, self.config),
                "dataset_sha256": dataset_sha256(self.rows, self.channels),
            }
            raw = json.dumps(prereg, sort_keys=True, separators=(",", ":")).encode("utf-8")
            path = root / "prereg.json"
            path.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            stats = self.dataset.open_test_split(
                preregistration_path=path,
                preregistration_sha256=digest,
                access_log_path=root / "access.jsonl",
            )
            self.assertEqual(stats.split, "test")
            batches = list(self.dataset.iter_batches("test", batch_size=32))
            self.assertTrue(batches)
            event = json.loads((root / "access.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(event["preregistration_sha256"], digest)

    def test_test_access_fails_closed_when_audit_log_cannot_be_written(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prereg = {
                "data_config_sha256": data_config_sha256(self.config),
                "split_boundaries_sha256": split_boundaries_sha256(self.rows, self.config),
                "dataset_sha256": dataset_sha256(self.rows, self.channels),
            }
            raw = json.dumps(prereg, sort_keys=True, separators=(",", ":")).encode("utf-8")
            path = root / "prereg.json"
            path.write_bytes(raw)
            log_directory = root / "not-a-file"
            log_directory.mkdir()
            with self.assertRaises(OSError):
                self.dataset.open_test_split(
                    preregistration_path=path,
                    preregistration_sha256=hashlib.sha256(raw).hexdigest(),
                    access_log_path=log_directory,
                )
            with self.assertRaises(PermissionError):
                next(self.dataset.iter_batches("test", batch_size=8))

    def test_test_preregistration_rejects_data_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prereg = {
                "data_config_sha256": data_config_sha256(self.config),
                "split_boundaries_sha256": split_boundaries_sha256(self.rows, self.config),
                "dataset_sha256": "0" * 64,
            }
            raw = json.dumps(prereg, sort_keys=True, separators=(",", ":")).encode("utf-8")
            path = root / "prereg.json"
            path.write_bytes(raw)
            with self.assertRaisesRegex(PermissionError, "dataset_sha256"):
                self.dataset.open_test_split(
                    preregistration_path=path,
                    preregistration_sha256=hashlib.sha256(raw).hexdigest(),
                    access_log_path=root / "access.jsonl",
                )
            self.assertFalse((root / "access.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
