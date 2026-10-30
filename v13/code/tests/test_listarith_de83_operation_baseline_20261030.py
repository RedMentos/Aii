"""Source-only diagnostic tests for seed83 frozen operation baseline."""
import unittest

from scripts.listarith_de83_operation_baseline import baseline, FIXTURE_BLOB


class Seed83OperationBaselineTests(unittest.TestCase):
    def test_frozen_baseline_coverage_and_negative_gates(self):
        report = baseline()
        self.assertEqual(report["fixture_blob"], FIXTURE_BLOB)
        self.assertEqual(len(report["rows"]), 24)
        self.assertEqual(report["exact_total"],
                         sum(r["correct"] for r in report["rows"]))
        self.assertEqual(report["exact_supported"],
                         sum(r["correct"] for r in report["rows"]
                             if r["expected_operation"] is not None))
        self.assertEqual(report["exact_unsupported"],
                         sum(r["correct"] for r in report["rows"]
                             if r["expected_operation"] is None))
        self.assertFalse(report["live_tool_execution"])
        self.assertEqual(report["native_model_calls"], 0)
        self.assertFalse(report["step2_gate_promoted"])
        self.assertFalse(report["b3_promoted"])
        self.assertFalse(report["body_jepa_available"])
        self.assertFalse(report["whole_system_complete"])


if __name__ == "__main__":
    unittest.main()
