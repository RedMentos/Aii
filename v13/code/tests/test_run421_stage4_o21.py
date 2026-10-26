"""Run421 source-only stage4 O_s21 continuation and native safety tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run421_stage4_o21 as stage
from tests.test_run419_verify_stage3_native import Run419Native126Tests


class Run421Stage4Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = Run419Native126Tests("test_all_three_receipts_checked_before_green")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root.parent
        self.source = self.fixture.root
        self.report = self.fixture.report
        self.receipt = self.fixture.receipt

    def installed(self):
        root = self.root / "installed"
        (root / "bin").mkdir(parents=True, exist_ok=True)
        (root / "bin/llama-server").write_bytes(b"synthetic only")
        return root

    def sha_for_runner(self):
        original = stage.safe.sha_file
        def selective(path):
            return (stage.RUN401_EXECUTABLE_SHA256
                    if Path(path).name == "llama-server" else original(path))
        return selective

    def test_source_only_restores_exact_126_without_native(self):
        with mock.patch.object(stage.resume, "validate_completed",
                               return_value=self.receipt), \
             mock.patch.object(stage.resume, "run") as native:
            report = stage.stage4(self.source, self.report, self.root / "work")
        native.assert_not_called()
        self.assertEqual(report["status"], "STAGE4_READY_NO_NATIVE")
        self.assertEqual(report["rows_verified"], 126)
        self.assertFalse(report["native_execute_attempted"])
        self.assertFalse(report["canonical_gate_pass"])
        self.assertFalse((self.root / "work" / stage.gate.MANIFEST).exists())

    def test_execute_requires_installed_home_and_safe_export(self):
        report = stage.stage4(self.source, self.report, self.root / "work",
                              execute=True)
        self.assertEqual(report["status"], "STAGE4_RED_PRESERVED")
        self.assertIn("INSTALLED_HOME_AND_SAFE_EXPORT_REQUIRED_FOR_EXECUTE",
                      report["errors"])
        self.assertFalse((self.root / "work").exists())

    def test_unverified_prior_native_receipt_blocks_next_arm(self):
        installed = self.installed()
        with mock.patch.object(stage.safe, "sha_file",
                               side_effect=self.sha_for_runner()), \
             mock.patch.object(stage.audit, "verify", return_value={
                 "status": "RUN419_NATIVE_126_INDEPENDENTLY_VERIFIED"}), \
             mock.patch.object(stage.resume, "validate_completed",
                               side_effect=ValueError("RECORDED_MODEL_IDENTITY_MISMATCH")), \
             mock.patch.object(stage.resume, "run") as native, \
             mock.patch.object(stage.safe, "export", return_value={
                 "status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS", "errors": []}):
            report = stage.stage4(self.source, self.report, self.root / "work",
                                  installed=installed, execute=True,
                                  export_dest=self.root / "out")
        native.assert_not_called()
        self.assertEqual(report["status"], "STAGE4_RED_PRESERVED")
        self.assertFalse(report["native_execute_attempted"])
        self.assertIn("RECORDED_MODEL_IDENTITY_MISMATCH", str(report["errors"]))

    def test_synthetic_one_o21_native_168_rows_never_promotes_gate(self):
        installed = self.installed()
        progress = json.loads((self.source / "RUN397_PROGRESS.json").read_text())
        progress["completed"]["O_s21"] = {
            "attempt": "attempts/O_s21/attempt-0001", "validated": self.receipt}
        result = {"status": "INCOMPLETE", "completed": progress["completed"],
                  "failures_preserved": {}, "canonical_gate_pass": False,
                  "step2_exit": "UTILITY_FAIL"}
        def native(work, *args, **kwargs):
            p = Path(work) / "RUN397_PROGRESS.json"
            p.write_text(json.dumps(progress))
            (Path(work) / "attempts/O_s21/attempt-0001").mkdir(
                parents=True, exist_ok=True)
            return result
        with mock.patch.object(stage.safe, "sha_file",
                               side_effect=self.sha_for_runner()), \
             mock.patch.object(stage.resume, "validate_completed",
                               return_value=self.receipt), \
             mock.patch.object(stage.resume, "run", side_effect=native) as called, \
             mock.patch.object(stage.safe, "export", return_value={
                 "status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS", "errors": []}):
            report = stage.stage4(self.source, self.report, self.root / "work",
                                  installed=installed, execute=True,
                                  export_dest=self.root / "out")
        called.assert_called_once()
        self.assertEqual(called.call_args.kwargs["max_new_arms"], 1)
        self.assertEqual(report["status"], "STAGE4_NATIVE_PARTIAL_NO_PROMOTION")
        self.assertEqual(report["rows_verified"], 168)
        self.assertEqual(report["completed"][-1], "O_s21")
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_exit"], "UTILITY_FAIL")

    def test_wrong_next_arm_cannot_claim_native_168(self):
        installed = self.installed()
        result = {"status": "INCOMPLETE", "completed": {
            rid: {"attempt": "attempts/" + rid + "/attempt-0001",
                  "validated": self.receipt}
            for rid in ("O_s20", "P_s20", "S_s20", "P_s21")},
            "failures_preserved": {}, "canonical_gate_pass": False,
            "step2_exit": "UTILITY_FAIL"}
        with mock.patch.object(stage.safe, "sha_file",
                               side_effect=self.sha_for_runner()), \
             mock.patch.object(stage.resume, "validate_completed",
                               return_value=self.receipt), \
             mock.patch.object(stage.resume, "run", return_value=result), \
             mock.patch.object(stage.safe, "export", return_value={
                 "status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS", "errors": []}):
            report = stage.stage4(self.source, self.report, self.root / "work",
                                  installed=installed, execute=True,
                                  export_dest=self.root / "out")
        self.assertEqual(report["status"], "STAGE4_RED_PRESERVED")
        self.assertIn("STAGE4_NEXT_ARM_NOT_COMPLETE", str(report["errors"]))
        self.assertFalse(report["native_execution_performed"])

    def test_tampered_source_rejected_before_destination(self):
        (self.source / "attempts/S_s20/attempt-0001/native.json").write_text("bad")
        with mock.patch.object(stage.resume, "run") as native:
            report = stage.stage4(self.source, self.report, self.root / "work")
        native.assert_not_called()
        self.assertEqual(report["status"], "STAGE4_RED_PRESERVED")
        self.assertFalse((self.root / "work").exists())


if __name__ == "__main__":
    unittest.main()
