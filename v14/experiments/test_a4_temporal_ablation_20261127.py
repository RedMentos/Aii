"""Regression tests for the deterministic A4 temporal source-isolation probe."""
import unittest

from a4_temporal_ablation_20261127 import run_experiment


class A4TemporalAblationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_experiment()

    def test_environment_and_data_boundary_are_explicit(self):
        self.assertEqual(self.result["environment"], "SYNTHETIC")
        self.assertTrue(self.result["synthetic_benchmark"])
        self.assertFalse(self.result["device_benchmark"])
        self.assertFalse(self.result["raw_audio_persisted"])
        self.assertFalse(self.result["training_examples_persisted"])

    def test_independent_streams_are_identical_when_interleaved(self):
        isolation = self.result["source_isolation"]
        self.assertTrue(isolation["interleaved_equals_isolated"])
        self.assertEqual(isolation["max_metric_difference"], 0.0)

    def test_existing_predictor_updates_numeric_parameters_against_baseline(self):
        aggregate = self.result["aggregate"]
        self.assertTrue(aggregate["parameter_delta_nonzero"])
        self.assertLessEqual(aggregate["max_attention_novelty"], aggregate["attention_gain_cap"])
        self.assertLessEqual(aggregate["max_omission_attention_novelty"], aggregate["attention_gain_cap"])
        for metrics in self.result["per_source"].values():
            self.assertGreater(metrics["measured_windows"], 0)
            self.assertIsNotNone(metrics["mean_model_mae"])
            self.assertIsNotNone(metrics["mean_persistence_baseline_mae"])
            self.assertIsNotNone(metrics["mean_improvement_mae"])
            self.assertGreater(metrics["max_parameter_l2"], 0.0)

    def test_no_context_negative_control_never_learns_or_emits_novelty(self):
        control = self.result["no_context_control"]
        self.assertEqual(control["measured_windows"], 0)
        self.assertEqual(control["max_attention_novelty"], 0.0)
        self.assertEqual(control["final_stream_count"], 0)

    def test_provisional_windows_are_censored(self):
        control = self.result["provisional_control"]
        self.assertEqual(control["status"], "PROVISIONAL_IGNORED")
        self.assertEqual(control["stream_count"], 0)
        self.assertEqual(control["updates"], 0)

    def test_consent_rotation_resets_ephemeral_numeric_state(self):
        control = self.result["consent_reset_control"]
        self.assertEqual(control["status"], "RESET_CONSENT_SCOPE")
        self.assertEqual(control["updates"], 0)
        self.assertEqual(control["parameter_l2"], 0.0)
        self.assertFalse(control["weight_persistence"])


if __name__ == "__main__":
    unittest.main()
