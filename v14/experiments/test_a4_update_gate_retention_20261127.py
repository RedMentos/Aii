"""Tests for the synthetic A4 error-gated plasticity and restart ablation."""
import unittest

from a4_update_gate_retention_20261127 import run_experiment


class A4UpdateGateRetentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_experiment()

    def test_environment_and_privacy_boundary_are_explicit(self):
        self.assertEqual(self.result["environment"], "SYNTHETIC")
        self.assertTrue(self.result["synthetic_benchmark"])
        self.assertFalse(self.result["device_benchmark"])
        self.assertEqual(self.result["schema"], "v14.a4.error-gated-plasticity/2")
        self.assertEqual(self.result["update_policy_default"], "EVERY_FINAL")
        for result in self.result["retention_restart"].values():
            self.assertFalse(result["raw_audio_or_feature_windows_persisted"])
            self.assertFalse(result["gate_memory_persisted"])

    def test_memorized_error_gate_never_updates_more_than_every_final(self):
        for source, policies in self.result["per_source"].items():
            every = policies["EVERY_FINAL"]
            gated = policies["MEMORIZED_ERROR"]
            self.assertLessEqual(gated["updates"], every["updates"])
            self.assertLessEqual(gated["update_fraction"], every["update_fraction"])
            self.assertEqual(set(gated["state_dict_fields"]), {"updates", "weights"})
            self.assertLessEqual(gated["max_mistake_memory_entries"], self.result["memory_capacity"])

    def test_transient_consolidation_has_real_persistent_and_effective_parameter_diffs(self):
        results = [
            self.result["per_source"][source]["TRANSIENT_CONSOLIDATE"]
            for source in self.result["per_source"]
        ]
        self.assertGreater(max(item["consolidations"] for item in results), 0)
        self.assertGreater(max(item["persistent_parameter_l2"] for item in results), 0.0)
        for item in results:
            self.assertGreaterEqual(item["transient_updates"], item["consolidations"])
            self.assertLessEqual(item["transient_parameter_l2"], item["max_transient_norm"] + 1e-8)
            self.assertEqual(set(item["state_dict_fields"]), {"updates", "weights"})

    def test_no_consolidation_control_changes_only_ephemeral_parameters(self):
        for source, policies in self.result["per_source"].items():
            control = policies["TRANSIENT_NO_CONSOLIDATION"]
            self.assertEqual(control["persistent_updates"], 0)
            self.assertEqual(control["consolidations"], 0)
            self.assertEqual(control["parameter_diff_l2_from_initial"], 0.0)
            self.assertGreater(control["effective_parameter_diff_l2_from_initial"], 0.0)
            self.assertGreater(control["transient_parameter_l2"], 0.0)
            self.assertLessEqual(control["transient_parameter_l2"], control["max_transient_norm"] + 1e-8)

    def test_no_update_baseline_has_zero_weight_change(self):
        for source, policies in self.result["per_source"].items():
            baseline = policies["NO_UPDATE"]
            self.assertEqual(baseline["updates"], 0)
            self.assertEqual(baseline["gradient_updates"], 0)
            self.assertEqual(baseline["gradient_l2_sum"], 0.0)
            self.assertEqual(baseline["total_weight_delta_l2"], 0.0)
            self.assertEqual(baseline["parameter_diff_l2_from_initial"], 0.0)

    def test_gate_reduces_updates_on_at_least_one_stream(self):
        reductions = [
            self.result["per_source"][source]["EVERY_FINAL"]["updates"]
            - self.result["per_source"][source]["MEMORIZED_ERROR"]["updates"]
            for source in self.result["per_source"]
        ]
        self.assertGreater(max(reductions), 0)

    def test_retention_evaluation_is_read_only_and_restart_exact(self):
        for policy, result in self.result["retention_restart"].items():
            self.assertTrue(result["numeric_weights_equal_after_restart"])
            if policy in {"EVERY_FINAL", "MEMORIZED_ERROR", "FEATURE_ERROR_GATED", "NO_UPDATE"}:
                self.assertTrue(result["restart_prediction_error_equal"])
            self.assertEqual(
                result["pending_transient_delta_dropped"],
                result["transient_parameter_l2_before_restart"] > 0.0,
            )
            self.assertEqual(result["transient_parameter_l2_after_restart"], 0.0)
            self.assertTrue(result["old_pattern_after_restart"]["evaluation_only"])
            self.assertEqual(result["old_pattern_after_restart"]["update_count"], result["old_pattern_after_new_task"]["update_count"])
            self.assertEqual(result["gate_memory_entries_after_restart"], 0)
            self.assertIsNotNone(result["retention_error_delta"])


    def test_feature_error_gated_policy_is_measured_per_source(self):
        for source, policies in self.result["per_source"].items():
            gated = policies["FEATURE_ERROR_GATED"]
            every = policies["EVERY_FINAL"]
            self.assertLessEqual(gated["updates"], every["updates"])
            self.assertGreaterEqual(gated["feature_error_observations"], gated["updated_feature_observations"])
            self.assertGreaterEqual(gated["updated_feature_fraction"], 0.0)
            self.assertLessEqual(gated["updated_feature_fraction"], 1.0)
            self.assertEqual(set(gated["state_dict_fields"]), {"updates", "weights"})

    def test_feature_error_gated_retention_restart_is_exact(self):
        result = self.result["retention_restart"]["FEATURE_ERROR_GATED"]
        self.assertTrue(result["numeric_weights_equal_after_restart"])
        self.assertTrue(result["restart_prediction_error_equal"])
        self.assertTrue(result["old_pattern_after_restart"]["evaluation_only"])
        self.assertEqual(result["transient_parameter_l2_after_restart"], 0.0)
        self.assertFalse(result["gate_memory_persisted"])
        self.assertFalse(result["raw_audio_or_feature_windows_persisted"])

    def test_experiment_does_not_claim_device_or_master_weight_learning(self):
        claims = " ".join(self.result["not_claimed"])
        self.assertIn("Android", claims)
        self.assertIn("master-weight", claims)
        self.assertIn("latent", claims)


if __name__ == "__main__":
    unittest.main()
