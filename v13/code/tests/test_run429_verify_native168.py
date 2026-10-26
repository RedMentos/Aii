"""Run429 source-only negative tests for 168-row native report integrity."""
import copy
import tempfile
import unittest
from pathlib import Path
from scripts import run429_verify_native168 as A


def good():
    return {
        "run": "Run421", "status": "STAGE4_NATIVE_PARTIAL_NO_PROMOTION",
        "errors": [], "native_execute_requested": True,
        "native_execute_attempted": True, "native_execution_performed": True,
        "rows_verified": 168, "completed": list(A.PREFIX), "remaining_arms": 5,
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "redmi_measured": False, "jepa_weight": 0,
        "safe_export": {"status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS",
                        "errors": [], "manifest_sha256": "0" * 64,
                        "copied_files": 115, "copied_bytes": 81562039},
    }


class Run429Native168(unittest.TestCase):
    def test_exact_report_shape_accepted_only_as_partial(self):
        self.assertEqual(A.ROWS, 168)
        self.assertEqual(A.PREFIX, ("O_s20", "P_s20", "S_s20", "O_s21"))
        self.assertEqual(A.validate_report(good())["status"],
                         "EXPORT_VERIFIED_NO_MODEL_WEIGHTS")

    def test_all_gate_promotions_and_missing_native_rejected(self):
        mutations = [
            ("canonical_gate_pass", True),
            ("step2_exit", "PASS"),
            ("redmi_measured", True),
            ("jepa_weight", 0.0),
            ("jepa_weight", 1),
            ("native_execution_performed", False),
            ("native_execute_attempted", False),
            ("rows_verified", 126),
            ("rows_verified", 378),
            ("remaining_arms", 4),
            ("status", "STAGE4_READY_NO_NATIVE"),
            ("errors", ["fake success"]),
            ("completed", list(A.PREFIX[:-1])),
            ("completed", list(reversed(A.PREFIX))),
        ]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                r = good()
                r[field] = value
                with self.assertRaisesRegex(ValueError, "RUN427_NATIVE_168_NOT_GREEN"):
                    A.validate_report(r)

    def test_export_red_refused(self):
        for field, value in (("status", "EXPORT_RED"), ("errors", ["missing"])):
            r = good()
            r["safe_export"][field] = value
            with self.assertRaisesRegex(ValueError, "RUN427_SAFE_EXPORT_NOT_GREEN"):
                A.validate_report(r)

    def test_missing_actual_export_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                A.verify(Path(tmp) / "missing", good())


if __name__ == "__main__":
    unittest.main()
