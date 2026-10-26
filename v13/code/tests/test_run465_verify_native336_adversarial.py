"""Run465 independent source-only adversarial review of eight native336 receipts.

Builds eight synthetic receipts from the inherited Run434 fixture. No model
inference, no claim of actual native336 evidence, no edit to active Run453 owner.
"""
import hashlib
import json
import unittest
from unittest import mock

from scripts import run465_verify_native336 as A
from tests.test_run434_stage5_p21 import Run434Stage5Tests


class Run465EightReceiptAdversarial(unittest.TestCase):
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
        for rid in ("P_s21", "S_s21", "O_s22", "P_s22"):
            progress["completed"][rid] = {
                "attempt": f"attempts/{rid}/attempt-0001", "validated": self.receipt}
            name = f"attempts/{rid}/attempt-0001/native.json"
            path = self.source / name
            path.parent.mkdir(parents=True)
            path.write_bytes(b'{"synthetic":true}')
            self.fixture.fixture.manifest["directories"] += [
                f"attempts/{rid}", f"attempts/{rid}/attempt-0001"]
            raw = path.read_bytes()
            self.fixture.fixture.manifest["copied"][name] = {
                "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        progress_path.write_text(json.dumps(progress))
        raw = progress_path.read_bytes()
        self.fixture.fixture.manifest["copied"]["RUN397_PROGRESS.json"] = {
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        self.report.update({
            "run": "Run462", "status": "STAGE8_NATIVE_PARTIAL_NO_PROMOTION",
            "rows_verified": 336, "completed": list(A.PREFIX),
            "remaining_arms": 1, "progress_sha256": A.sha_file(progress_path)})
        self.report["safe_export"]["copied_files"] = len(
            self.fixture.fixture.manifest["copied"])
        self.report["safe_export"]["copied_bytes"] = sum(
            x["bytes"] for x in self.fixture.fixture.manifest["copied"].values())
        self.fixture.fixture.seal()

    def test_all_eight_receipts_verified_before_scoped_result(self):
        with mock.patch.object(A.r397, "validate_completed",
                               return_value=self.receipt) as checked:
            result = A.verify(self.source, self.report)
        self.assertEqual(result["status"], "RUN465_NATIVE_336_INDEPENDENTLY_VERIFIED")
        self.assertEqual(result["rows_verified"], 336)
        self.assertEqual(checked.call_count, 8)
        self.assertEqual(result["verified_arms"][-1], "P_s22")
        self.assertFalse(result["canonical_gate_pass"])
        self.assertEqual(result["step2_exit"], "UTILITY_FAIL")
        self.assertFalse(result["redmi_measured"])

    def test_old_six_receipt_report_and_wrong_remaining_count_refused(self):
        self.report["rows_verified"] = 252
        with self.assertRaisesRegex(ValueError, "RUN465_NATIVE_336_NOT_GREEN"):
            A.verify(self.source, self.report)
        self.report["rows_verified"] = 336
        self.report["remaining_arms"] = 2
        with self.assertRaisesRegex(ValueError, "RUN465_NATIVE_336_NOT_GREEN"):
            A.verify(self.source, self.report)

    def test_eightth_receipt_source_identity_mismatch_refused(self):
        def invalid(directory, arm, seed, *args, **kwargs):
            if (arm, seed) == ("P", 22):
                return dict(self.receipt, sha256={"native.json": "0" * 64})
            return self.receipt
        with mock.patch.object(A.r397, "validate_completed", side_effect=invalid):
            with self.assertRaisesRegex(ValueError,
                                        "STAGE8_NATIVE_RECEIPT_INVALID:P_s22"):
                A.verify(self.source, self.report)

    def test_eightth_receipt_wrong_rows_refused(self):
        def invalid(directory, arm, seed, *args, **kwargs):
            return {"rows": 41} if (arm, seed) == ("P", 22) else self.receipt
        with mock.patch.object(A.r397, "validate_completed", side_effect=invalid):
            with self.assertRaisesRegex(ValueError,
                                        "STAGE8_NATIVE_RECEIPT_INVALID:P_s22"):
                A.verify(self.source, self.report)

    def test_tampered_eightth_file_rejected_before_receipt(self):
        (self.source / "attempts/P_s22/attempt-0001/native.json").write_bytes(b"tampered")
        with mock.patch.object(A.r397, "validate_completed") as checked:
            with self.assertRaisesRegex(ValueError,
                                        "EXPORT_FILE_METADATA_INVALID|EXPORT_HASH"):
                A.verify(self.source, self.report)
            checked.assert_not_called()

    def test_unlisted_file_and_gate_promotion_rejected(self):
        (self.source / "extra.txt").write_bytes(b"extra")
        with self.assertRaisesRegex(ValueError, "UNLISTED_EXPORT_FILE"):
            A.verify(self.source, self.report)
        (self.source / "extra.txt").unlink()
        self.report["canonical_gate_pass"] = True
        with self.assertRaisesRegex(ValueError, "RUN465_NATIVE_336_NOT_GREEN"):
            A.verify(self.source, self.report)

    def test_symlinked_eightth_file_rejected(self):
        target = self.source / "attempts/P_s22/attempt-0001/native.json"
        target.unlink()
        target.symlink_to(self.source / "RUN397_PROGRESS.json")
        with self.assertRaisesRegex(ValueError, "EXPORT_SYMLINK_FILE"):
            A.verify(self.source, self.report)


if __name__ == "__main__":
    unittest.main()
