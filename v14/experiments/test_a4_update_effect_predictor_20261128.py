"""Tests for the synthetic A4 update-effect/future-regime research ablation."""
import math
import unittest

from a4_update_effect_predictor_20261128 import (
    _aligned_candidate_pair,
    _deltas,
    _smooth_sequence,
    run_experiment,
)
from v13.audio_temporal_prediction import AudioTemporalPredictor


class A4UpdateEffectPredictorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_experiment()

    def test_scope_and_training_holdout_split_are_explicit(self):
        result = self.result
        self.assertEqual(result["schema"], "v14.a4.update-effect-predictor/2")
        self.assertEqual(
            result["counterfactual_state_alignment"],
            "CANDIDATE_AND_NO_UPDATE_BASELINE_ADVANCE_THROUGH_SAME_CURRENT_WINDOW",
        )
        self.assertEqual(result["environment"], "SYNTHETIC")
        self.assertTrue(result["synthetic_benchmark"])
        self.assertFalse(result["device_benchmark"])
        self.assertFalse(result["predictor"]["test_labels_used_for_fit"])
        self.assertTrue(set(result["training_sessions"]).isdisjoint(result["heldout_sessions"]))
        self.assertFalse(result["privacy"]["raw_audio_persisted"])
        self.assertFalse(result["privacy"]["feature_windows_persisted"])
        self.assertFalse(result["privacy"]["training_examples_persisted"])
        self.assertFalse(result["authority"]["runtime_policy_changed"])
        self.assertFalse(result["authority"]["weight_persistence"])

    def test_candidate_and_no_update_baseline_share_current_window(self):
        deltas = _deltas(_smooth_sequence(0, 0.55))
        predictor = AudioTemporalPredictor(
            learning_rate=0.20,
            warmup_updates=1,
            update_policy="FEATURE_ERROR_GATED",
        )
        predictor.update(deltas[0], allow_update=False)
        baseline, candidate, _result = _aligned_candidate_pair(
            predictor, deltas[1]
        )
        self.assertEqual(candidate._previous, baseline._previous)
        self.assertEqual(baseline.state_dict(), predictor.state_dict())

    def test_smooth_and_abrupt_regimes_compare_all_controls(self):
        self.assertEqual(set(self.result["per_regime"]), {"smooth", "abrupt"})
        for policies in self.result["per_regime"].values():
            self.assertEqual(
                set(policies),
                {"EVERY_FINAL", "FEATURE_ERROR_GATED", "META_GATE", "NO_UPDATE"},
            )
            for result in policies.values():
                self.assertIsNotNone(result["current_eval"]["mean_model_mae"])
                self.assertIsNotNone(result["current_eval"]["mean_persistence_baseline_mae"])
                self.assertTrue(math.isfinite(result["old_task_retention_error_delta"]))
                self.assertTrue(result["evaluation_only"])

    def test_meta_gate_only_selects_candidate_feature_gated_updates(self):
        for policies in self.result["per_regime"].values():
            meta = policies["META_GATE"]
            self.assertLessEqual(meta["selected_updates"], meta["candidate_updates"])
            self.assertEqual(meta["selected_updates"], meta["updates"])

    def test_no_update_negative_control_has_zero_parameter_change(self):
        for policies in self.result["per_regime"].values():
            result = policies["NO_UPDATE"]
            self.assertEqual(result["updates"], 0)
            self.assertEqual(result["parameter_diff_l2"], 0.0)

    def test_every_final_control_has_numeric_parameter_change(self):
        for policies in self.result["per_regime"].values():
            result = policies["EVERY_FINAL"]
            self.assertGreater(result["updates"], 0)
            self.assertGreater(result["parameter_diff_l2"], 0.0)

    def test_meta_predictor_is_fitted_and_training_effects_are_nonconstant(self):
        result = self.result
        self.assertGreaterEqual(result["training_examples"], 16)
        self.assertGreater(result["training_label_max"], result["training_label_min"])
        self.assertTrue(math.isfinite(result["predictor"]["residual_rmse"]))
        self.assertEqual(result["predictor"]["coefficients"], 8)

    def test_experiment_is_deterministic(self):
        self.assertEqual(self.result, run_experiment())


if __name__ == "__main__":
    unittest.main()
