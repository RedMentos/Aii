"""Tests for the multi-horizon A4 update-effect research ablation."""

import math
import unittest

from a4_multi_horizon_update_effect_20261128 import (
    _abrupt_to_smooth_sequence,
    _select_multi_horizon,
    run_experiment,
)


class MultiHorizonUpdateEffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_experiment()

    def test_split_and_replay_anchor_independence(self):
        result = self.result
        self.assertFalse(result["training_anchor_shared_with_test"])
        self.assertFalse(result["test_labels_used_for_fit"])
        self.assertFalse(result["future_labels_used_at_decision"])
        self.assertFalse(result["deployed_checkpoint_available"])
        self.assertEqual(
            result["reference_checkpoint"],
            "SYNTHETIC_NO_UPDATE_BASELINE_NOT_DEPLOYED_C0",
        )
        self.assertNotEqual(
            result["training_replay_anchor"]["sha256"],
            result["heldout_replay_anchors"]["heldout-periodic"]["sha256"],
        )
        self.assertNotEqual(
            result["training_replay_anchor"]["sha256"],
            result["heldout_replay_anchors"]["heldout-noise"]["sha256"],
        )
        self.assertTrue(
            set(result["training_sessions"]).isdisjoint(
                result["heldout_sessions"]
            )
        )

    def test_abrupt_to_smooth_fixture_has_both_regimes(self):
        rows = _abrupt_to_smooth_sequence(1, 24, 96)
        self.assertTrue(all(
            row["activity_hint"] in {"IMPULSIVE", "UNVOICED_NOISE"}
            for row in rows[:24]
        ))
        self.assertTrue(any(
            row["activity_hint"] == "VOICED" for row in rows[24:]
        ))

    def test_horizons_and_regimes(self):
        result = self.result
        self.assertEqual(result["horizons"], [1, 3, 8])
        self.assertEqual(
            set(result["per_regime"]),
            {"smooth", "abrupt", "abrupt_to_smooth"},
        )
        expected_policies = {
            "EVERY_FINAL",
            "FEATURE_ERROR_GATED",
            "ONE_STEP_META_GATE",
            "MULTI_HORIZON_META_GATE",
            "NO_UPDATE",
        }
        for policies in result["per_regime"].values():
            self.assertEqual(set(policies), expected_policies)
            for item in policies.values():
                self.assertTrue(item["evaluation_only"])
                self.assertTrue(math.isfinite(
                    item["current_improvement_vs_persistence"]
                ))
                self.assertTrue(math.isfinite(
                    item["worst_old_task_retention_error_delta"]
                ))
                self.assertEqual(
                    set(item["horizon_metrics"]), {"1", "3", "8"}
                )
                self.assertIn(
                    item["synthetic_reference_verdict"],
                    {"PASS", "NO_IMPROVEMENT", "REGRESSION"},
                )

    def test_negative_and_positive_controls(self):
        for policies in self.result["per_regime"].values():
            no_update = policies["NO_UPDATE"]
            self.assertEqual(no_update["updates"], 0)
            self.assertEqual(no_update["parameter_diff_l2"], 0.0)
            every_final = policies["EVERY_FINAL"]
            self.assertGreater(every_final["updates"], 0)
            self.assertGreater(every_final["parameter_diff_l2"], 0.0)

    def test_gate_is_conservative_across_horizons(self):
        self.assertTrue(
            _select_multi_horizon([0.03, 0.02, 0.01], [0.005, 0.005, 0.005])
        )
        self.assertFalse(
            _select_multi_horizon([0.03, -0.1, 0.02], [0.005, 0.005, 0.005])
        )
        for policies in self.result["per_regime"].values():
            meta = policies["MULTI_HORIZON_META_GATE"]
            self.assertLessEqual(meta["selected_updates"], meta["candidate_updates"])
            self.assertGreaterEqual(meta["abstention_fraction"], 0.0)
            self.assertLessEqual(meta["abstention_fraction"], 1.0)
            for metric in meta["horizon_metrics"].values():
                self.assertGreaterEqual(metric["counterfactual_regret"], 0.0)

    def test_heads_fit_on_earlier_sessions_only(self):
        for model in self.result["predictors"].values():
            self.assertEqual(model["coefficients"], 8)
            self.assertGreaterEqual(model["residual_rmse"], 0.0)

    def test_experiment_is_deterministic(self):
        self.assertEqual(self.result, run_experiment())


if __name__ == "__main__":
    unittest.main()
