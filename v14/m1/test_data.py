"""Synthetic logic tests for the V14 M1 DATA pipeline.

Run from repository root:
    python -m unittest v14.m1.test_data -v

These tests validate pipeline logic only. They are not a UCI real-data run.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from v14.m1.data import (
    DataConfig,
    MinuteRow,
    build_chronological_boundaries,
    build_dataset,
    make_split,
    parse_uci,
    write_manifest,
    data_config_sha256,
    split_boundaries_sha256,
    dataset_sha256,
    load_test_split,
)


def synthetic_rows(n: int, missing_at: set[int] | None = None):
    missing_at = missing_at or set()
    start = datetime(2020, 1, 1)
    rows = []
    for i in range(n):
        a = None if i in missing_at else float(i)
        rows.append(MinuteRow(start + timedelta(minutes=i), (a, float(i * 2))))
    return rows


class DataConfigTests(unittest.TestCase):
    def config(self, input_length=5):
        return DataConfig(
            input_length=input_length,
            horizon=2,
            max_candidate_input_length=5,
            seasonal_lags=(2, 4),
            train_fraction=0.70,
            validation_fraction=0.15,
        )

    def test_split_is_identical_across_pilot_L_values(self):
        a = build_chronological_boundaries(1000, self.config(3))
        b = build_chronological_boundaries(1000, self.config(5))
        self.assertEqual(a, b)

    def test_L_above_preregistered_max_is_rejected(self):
        with self.assertRaises(ValueError):
            self.config(6)

    def test_seasonal_lag_shorter_than_horizon_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "seasonal lag"):
            DataConfig(input_length=5, horizon=3, max_candidate_input_length=5, seasonal_lags=(2, 4))

    def test_split_gap_cannot_be_reduced(self):
        with self.assertRaises(ValueError):
            DataConfig(
                input_length=5, horizon=2, max_candidate_input_length=5,
                seasonal_lags=(2, 4), split_gap=6,
            ).effective_gap

    def test_gap_separates_raw_split_ranges(self):
        cfg = self.config()
        bounds = build_chronological_boundaries(1000, cfg)
        self.assertGreaterEqual(bounds["validation"][0] - bounds["train"][1], cfg.effective_gap)
        self.assertGreaterEqual(bounds["test"][0] - bounds["validation"][1], cfg.effective_gap)


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.rows = synthetic_rows(1000)
        self.channels = ("Global_active_power", "Voltage")
        self.cfg = DataConfig(
            input_length=5, horizon=2, max_candidate_input_length=5,
            seasonal_lags=(2, 4), train_fraction=0.70, validation_fraction=0.15,
        )
        self.bounds = build_chronological_boundaries(len(self.rows), self.cfg)

    def test_window_shapes_and_known_past_lags(self):
        windows, _ = make_split(self.rows, self.channels, self.cfg, "train", self.bounds["train"])
        self.assertTrue(windows)
        w = windows[-1]
        self.assertEqual(len(w.x), 5)
        self.assertEqual(len(w.target), 2)
        self.assertEqual(len(w.seasonal), 2)
        self.assertEqual(len(w.seasonal[0]), 4)  # two lags x two channels
        self.assertTrue(all(w.origin_index + j - lag <= w.origin_index
                            for j in (1, 2) for lag in self.cfg.seasonal_lags))
        self.assertEqual(w.seasonal[0], (
            float(w.origin_index - 1), float((w.origin_index - 1) * 2),
            float(w.origin_index - 3), float((w.origin_index - 3) * 2),
        ))
        lo, hi = self.bounds["train"]
        self.assertTrue(all(lo <= item.origin_index < hi for item in windows))
        self.assertTrue(all(item.origin_index + self.cfg.horizon < hi for item in windows))

    def test_strict_nan_rejects_window_when_any_required_channel_is_missing(self):
        rows = synthetic_rows(1000, {100})
        windows, stats = make_split(rows, self.channels, self.cfg, "train", self.bounds["train"])
        self.assertGreater(stats.rejected_windows, 0)
        affected = [w for w in windows if abs(w.origin_index - 100) <= 4]
        self.assertFalse(affected)

    def test_missing_seasonal_source_rejects_window(self):
        # Index 50 is outside the local X/target window around origin 100,
        # but is required by the lag-50 seasonal channel for that forecast.
        cfg = DataConfig(
            input_length=5, horizon=2, max_candidate_input_length=5,
            seasonal_lags=(50,), train_fraction=0.70, validation_fraction=0.15,
        )
        rows = synthetic_rows(1000, {50})
        bounds = build_chronological_boundaries(len(rows), cfg)
        windows, stats = make_split(rows, self.channels, cfg, "train", bounds["train"])
        self.assertGreater(stats.rejected_windows, 0)
        self.assertNotIn(100, [item.origin_index for item in windows])

    def test_rejection_stats_are_per_month_and_reconcile(self):
        rows = synthetic_rows(1000, {100, 101, 400})
        _, stats = make_split(rows, self.channels, self.cfg, "train", self.bounds["train"])
        self.assertEqual(sum(stats.accepted_by_month.values()), stats.accepted_windows)
        self.assertEqual(sum(stats.rejected_by_month.values()), stats.rejected_windows)
        self.assertAlmostEqual(
            stats.rejection_fraction,
            stats.rejected_windows / stats.candidate_windows,
        )

    def test_manifest_contains_fixed_split_and_rejection_statistics(self):
        _, stats, manifest = build_dataset(self.rows, self.channels, self.cfg)
        self.assertEqual(manifest["effective_gap"], self.cfg.effective_gap)
        self.assertEqual(set(manifest["split_stats"]), {"train", "validation"})
        self.assertEqual(manifest["test_access"], "LOCKED_REQUIRES_HASH_BOUND_PREREGISTRATION")
        self.assertEqual(manifest["split_stats"]["train"]["accepted_windows"], stats["train"].accepted_windows)


    def test_test_split_is_not_materialized_by_default(self):
        datasets, stats, manifest = build_dataset(self.rows, self.channels, self.cfg)
        self.assertEqual(set(datasets), {"train", "validation"})
        self.assertNotIn("test", stats)
        self.assertNotIn("test", manifest["split_stats"])

    def test_test_loader_requires_exact_prereg_hash_and_matching_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prereg = {
                "data_config_sha256": data_config_sha256(self.cfg),
                "split_boundaries_sha256": split_boundaries_sha256(self.rows, self.cfg),
                "dataset_sha256": dataset_sha256(self.rows, self.channels),
            }
            raw = json.dumps(prereg, sort_keys=True, separators=(",", ":")).encode("utf-8")
            prereg_path = root / "prereg.json"
            prereg_path.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            log_path = root / "test-access.jsonl"
            with self.assertRaises(PermissionError):
                load_test_split(
                    self.rows, self.channels, self.cfg,
                    preregistration_path=prereg_path,
                    preregistration_sha256="0" * 64,
                    access_log_path=log_path,
                )
            windows, stats = load_test_split(
                self.rows, self.channels, self.cfg,
                preregistration_path=prereg_path,
                preregistration_sha256=digest,
                access_log_path=log_path,
            )
            self.assertTrue(windows)
            self.assertEqual(stats.split, "test")
            events = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(events), 1)
            self.assertEqual(json.loads(events[0])["preregistration_sha256"], digest)

    def test_test_loader_rejects_config_drift_even_with_valid_file_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prereg = {
                "data_config_sha256": data_config_sha256(self.cfg),
                "split_boundaries_sha256": split_boundaries_sha256(self.rows, self.cfg),
                "dataset_sha256": dataset_sha256(self.rows, self.channels),
            }
            raw = json.dumps(prereg, sort_keys=True, separators=(",", ":")).encode("utf-8")
            path = root / "prereg.json"
            path.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            changed = DataConfig(
                input_length=4, horizon=2, max_candidate_input_length=5,
                seasonal_lags=(2, 4), train_fraction=0.70, validation_fraction=0.15,
            )
            with self.assertRaises(PermissionError):
                load_test_split(
                    self.rows, self.channels, changed,
                    preregistration_path=path,
                    preregistration_sha256=digest,
                    access_log_path=root / "log.jsonl",
                )

    def test_manifest_hash_is_stable(self):
        _, _, manifest = build_dataset(self.rows, self.channels, self.cfg)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            first = write_manifest(manifest, path)
            second = write_manifest(manifest, path)
            self.assertEqual(first, second)
            self.assertEqual(len(first), 64)


class UCIParserTests(unittest.TestCase):
    def test_semicolon_and_decimal_comma_and_missing_marker(self):
        payload = (
            "Date;Time;Global_active_power;Voltage\n"
            "16/12/2006;17:24:00;4,216;234,840\n"
            "16/12/2006;17:25:00;?;234,760\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.txt"
            path.write_text(payload, encoding="utf-8")
            channels, rows = parse_uci(path)
        self.assertEqual(channels, ("Global_active_power", "Voltage"))
        self.assertEqual(rows[0].values, (4.216, 234.840))
        self.assertIsNone(rows[1].values[0])

    def test_non_finite_measurements_fail_closed(self):
        for token in ("inf", "-inf", "Infinity"):
            payload = (
                "Date;Time;Global_active_power\n"
                f"16/12/2006;17:24:00;{token}\n"
            )
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "nonfinite.txt"
                path.write_text(payload, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "non-finite"):
                    parse_uci(path)

    def test_nan_spellings_are_treated_as_missing(self):
        payload = (
            "Date;Time;Global_active_power;Voltage\n"
            "16/12/2006;17:24:00;NAN;234,840\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nan.txt"
            path.write_text(payload, encoding="utf-8")
            _, rows = parse_uci(path)
        self.assertIsNone(rows[0].values[0])


    def test_missing_minute_timestamp_fails_closed(self):
        payload = (
            "Date;Time;Global_active_power\n"
            "16/12/2006;17:24:00;1,0\n"
            "16/12/2006;17:26:00;2,0\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gap.txt"
            path.write_text(payload, encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_uci(path)

    def test_non_monotonic_timestamps_fail_closed(self):
        payload = (
            "Date;Time;Global_active_power\n"
            "16/12/2006;17:25:00;1,0\n"
            "16/12/2006;17:24:00;2,0\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.txt"
            path.write_text(payload, encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_uci(path)


if __name__ == "__main__":
    unittest.main()
