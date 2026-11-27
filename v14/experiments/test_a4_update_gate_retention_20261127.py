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
            self.assertTrue(result["restart_prediction_error_equal"])
            self.assertTrue(result["old_pattern_after_restart"]["evaluation_only"])
            self.assertEqual(result["old_pattern_after_restart"]["update_count"], result["old_pattern_after_new_task"]["update_count"])
            self.assertEqual(result["gate_memory_entries_after_restart"], 0)
            self.assertIsNotNone(result["retention_error_delta"])

    def test_experiment_does_not_claim_device_or_master_weight_learning(self):
        claims = " ".join(self.result["not_claimed"])
        self.assertIn("Android", claims)
        self.assertIn("master-weight", claims)
        self.assertIn("latent", claims)


if __name__ == "__main__":
    unittest.main()
