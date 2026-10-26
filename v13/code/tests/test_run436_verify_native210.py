"""Run436 source-only adversarial 210-row verifier tests; no actual native evidence."""
import copy
import hashlib
import json
import unittest
from pathlib import Path
from unittest import mock

from scripts import run436_verify_native210 as A
from tests.test_run434_stage5_p21 import Run434Stage5Tests


def good():
    return {
        "run": "Run434", "status": "STAGE5_NATIVE_PARTIAL_NO_PROMOTION",
        "errors": [], "native_execute_requested": True,
        "native_execute_attempted": True, "native_execution_performed": True,
        "rows_verified": 210, "completed": list(A.PREFIX), "remaining_arms": 4,
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "redmi_measured": False, "jepa_weight": 0,
        "safe_export": {"status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS",
                        "errors": [], "manifest_sha256": "0" * 64,
                        "copied_files": 120, "copied_bytes": 85000000}
    }


class Run436ReportGuards(unittest.TestCase):
    def test_exact_partial_shape_only(self):
        self.assertEqual(A.ROWS, 210)
        self.assertEqual(A.PREFIX,
                         ("O_s20", "P_s20", "S_s20", "O_s21", "P_s21"))
        self.assertEqual(A.validate_report(good())["status"],
                         "EXPORT_VERIFIED_NO_MODEL_WEIGHTS")

    def test_false_native_and_gate_promotions_refused(self):
        mutations = [
            ("run", "Run421"), ("status", "STAGE5_READY_NO_NATIVE"),
            ("errors", ["fake"]), ("native_execute_requested", False),
            ("native_execute_attempted", False), ("native_execution_performed", False),
            ("rows_verified", 168), ("rows_verified", 378),
            ("remaining_arms", 5), ("remaining_arms", 3),
            ("completed", list(A.PREFIX[:-1])),
            ("completed", list(reversed(A.PREFIX))),
            ("canonical_gate_pass", True), ("step2_exit", "PASS"),
            ("redmi_measured", True), ("jepa_weight", 0.0), ("jepa_weight", 1)
        ]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                report = good()
                report[field] = value
                with self.assertRaisesRegex(ValueError, "RUN435_NATIVE_210_NOT_GREEN"):
                    A.validate_report(report)

    def test_safe_export_red_refused(self):
        for field, value in (("status", "EXPORT_RED"), ("errors", ["missing"])):
            report = good()
            report["safe_export"][field] = value
            with self.assertRaisesRegex(ValueError, "RUN435_SAFE_EXPORT_NOT_GREEN"):
                A.validate_report(report)


class Run436FiveReceipts(unittest.TestCase):
    def setUp(self):
        self.fixture = Run434Stage5Tests("test_source_only_restores_168_without_native")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.source = self.fixture.source
        self.receipt = self.fixture.receipt
        self.report = self.fixture.report
        progress_path = self.source / "RUN397_PROGRESS.json"
        progress = json.loads(progress_path.read_text())
        progress["native_success_does_not_promote_step2"] = True
        progress["completed"]["P_s21"] = {
            "attempt": "attempts/P_s21/attempt-0001", "validated": self.receipt}
        progress_path.write_text(json.dumps(progress))
        name = "attempts/P_s21/attempt-0001/native.json"
        path = self.source / name
        path.parent.mkdir(parents=True)
        path.write_bytes(b'{"synthetic":true}')
        self.fixture.fixture.manifest["directories"] += [
            "attempts/P_s21", "attempts/P_s21/attempt-0001"]
        for name in (name, "RUN397_PROGRESS.json"):
            raw = (self.source / name).read_bytes()
            self.fixture.fixture.manifest["copied"][name] = {
                "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        self.report.update({
            "run": "Run434", "status": "STAGE5_NATIVE_PARTIAL_NO_PROMOTION",
            "rows_verified": 210, "completed": list(A.PREFIX),
            "remaining_arms": 4,
            "progress_sha256": A.sha_file(progress_path)})
        self.report["safe_export"]["copied_files"] = len(
            self.fixture.fixture.manifest["copied"])
        self.report["safe_export"]["copied_bytes"] = sum(
            x["bytes"] for x in self.fixture.fixture.manifest["copied"].values())
        self.fixture.fixture.seal()

    def test_all_five_receipts_checked_before_green(self):
        with mock.patch.object(A.r397, "validate_completed",
                               return_value=self.receipt) as checked:
            result = A.verify(self.source, self.report)
        self.assertEqual(result["status"], "RUN436_NATIVE_210_INDEPENDENTLY_VERIFIED")
        self.assertEqual(result["rows_verified"], 210)
        self.assertEqual(checked.call_count, 5)
        self.assertEqual({c.args[1] for c in checked.call_args_list}, {"O", "P", "S"})
        self.assertFalse(result["canonical_gate_pass"])

    def test_fifth_receipt_failure_refuses_all_210(self):
        def invalid(directory, arm, seed, *args, **kwargs):
            return {"rows": 41} if arm == "P" and seed == 21 else self.receipt
        with mock.patch.object(A.r397, "validate_completed", side_effect=invalid):
            with self.assertRaisesRegex(ValueError,
                                        "STAGE5_NATIVE_RECEIPT_INVALID:P_s21"):
                A.verify(self.source, self.report)

    def test_tampered_fifth_file_rejected_before_receipt(self):
        (self.source / "attempts/P_s21/attempt-0001/native.json").write_bytes(b"tamper")
        with mock.patch.object(A.r397, "validate_completed") as checked:
            with self.assertRaisesRegex(ValueError,
                                        "EXPORT_FILE_METADATA_INVALID|EXPORT_HASH"):
                A.verify(self.source, self.report)
            checked.assert_not_called()

    def test_unlisted_file_and_false_progress_refused(self):
        (self.source / "extra.txt").write_bytes(b"extra")
        with self.assertRaisesRegex(ValueError, "UNLISTED_EXPORT_FILE"):
            A.verify(self.source, self.report)


if __name__ == "__main__":
    unittest.main()
