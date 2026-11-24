"""Tests for paired temporal-block bootstrap semantics."""
from __future__ import annotations

import unittest

import numpy as np

from v14.m1.bootstrap import WindowErrorSeries, paired_block_bootstrap


class PairedBlockBootstrapTests(unittest.TestCase):
    def _series(self):
        # Four seven-day blocks, two seeds; candidate is exactly 0.5 MAE better.
        origins = np.arange(28 * 24, dtype=np.int64) * 60
        reference = np.repeat(np.array([1.0, 2.0, 3.0, 4.0]), 7 * 24)
        candidate = reference - 0.5
        return [
            WindowErrorSeries("reference", seed, origins.copy(), reference.copy())
            for seed in (11, 22)
        ] + [
            WindowErrorSeries("candidate", seed, origins.copy(), candidate.copy())
            for seed in (11, 22)
        ]

    def test_paired_blocks_produce_expected_delta_and_ci(self):
        result = paired_block_bootstrap(
            self._series(), reference_model="reference",
            block_days=7, n_resamples=300, seed=4,
        )
        candidate = result["models"]["candidate"]
        self.assertAlmostEqual(candidate["delta_vs_reference"], -0.5)
        self.assertAlmostEqual(candidate["delta_ci"][0], -0.5)
        self.assertAlmostEqual(candidate["delta_ci"][1], -0.5)
        self.assertEqual(result["n_blocks"], 4)
        self.assertEqual(candidate["seed_variance"], 0.0)

    def test_same_seed_must_exist_for_each_model(self):
        items = self._series()[:-1]
        with self.assertRaises(ValueError):
            paired_block_bootstrap(items, reference_model="reference", n_resamples=10)

    def test_forecast_origins_must_match_across_models_and_seeds(self):
        items = self._series()
        changed = items[-1]
        items[-1] = WindowErrorSeries(
            changed.model, changed.seed, changed.origin_minute_ids + 1, changed.primary_mae
        )
        with self.assertRaises(ValueError):
            paired_block_bootstrap(items, reference_model="reference", n_resamples=10)

    def test_results_are_deterministic_for_fixed_seed(self):
        first = paired_block_bootstrap(self._series(), reference_model="reference", n_resamples=50, seed=8)
        second = paired_block_bootstrap(self._series(), reference_model="reference", n_resamples=50, seed=8)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
