"""Run453 source-only report-shape and negative gate controls (not native proof)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run453_verify_native252 as audit


def report():
    return {"run": "Run452", "status": "STAGE6_NATIVE_PARTIAL_NO_PROMOTION",
            "errors": [], "native_execute_requested": True,
            "native_execute_attempted": True, "native_execution_performed": True,
            "rows_verified": 252, "completed": list(audit.PREFIX),
            "remaining_arms": 3, "canonical_gate_pass": False,
            "step2_exit": "UTILITY_FAIL", "redmi_measured": False,
            "jepa_weight": 0,
            "safe_export": {"status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS",
                            "errors": [], "manifest_sha256": "0" * 64}}


class Run453VerifierGuards(unittest.TestCase):
    def test_exact_six_receipt_report_is_only_shape_eligible(self):
        self.assertEqual(audit.ROWS, 252)
        self.assertEqual(audit.PREFIX[-1], "S_s21")
        self.assertEqual(audit.validate_report(report())["status"],
                         "EXPORT_VERIFIED_NO_MODEL_WEIGHTS")

    def test_false_native_or_gate_promotion_is_refused(self):
        for field, value in (("canonical_gate_pass", True),
                             ("redmi_measured", True),
                             ("jepa_weight", 1),
                             ("rows_verified", 210),
                             ("remaining_arms", 4),
                             ("native_execution_performed", False)):
            with self.subTest(field=field):
                bad = report()
                bad[field] = value
                with self.assertRaises(ValueError):
                    audit.validate_report(bad)

    def test_missing_s21_or_failed_export_refused(self):
        for change in ("missing_s21", "failed_export"):
            bad = report()
            if change == "missing_s21":
                bad["completed"].pop()
            else:
                bad["safe_export"]["status"] = "EXPORT_RED"
            with self.subTest(change=change), self.assertRaises(ValueError):
                audit.validate_report(bad)

    def test_missing_real_export_cannot_be_claimed_verified(self):
        with self.assertRaises((ValueError, OSError)):
            audit.verify(Path("/nonexistent-run453-native-export"), report())


if __name__ == "__main__":
    unittest.main()
