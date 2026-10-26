"""Run434 source-only P_s21 next-arm isolation; synthetic fixtures are NOT native proof."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import run434_stage5_p21 as stage
from tests.test_run419_verify_stage3_native import Run419Native126Tests


class Run434Stage5Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = Run419Native126Tests("test_all_three_receipts_checked_before_green")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root.parent
        self.source = self.fixture.root
        self.receipt = self.fixture.receipt
        self.report = self.fixture.report
        progress_path = self.source / "RUN397_PROGRESS.json"
        progress = json.loads(progress_path.read_text())
        progress["completed"]["O_s21"] = {
            "attempt": "attempts/O_s21/attempt-0001", "validated": self.receipt}
        progress_path.write_text(json.dumps(progress))
        name = "attempts/O_s21/attempt-0001/native.json"
        path = self.source / name
        path.parent.mkdir(parents=True)
        path.write_bytes(b'{"synthetic":true}')
        self.fixture.manifest["directories"] += [
            "attempts/O_s21", "attempts/O_s21/attempt-0001"]
        for name in (name, "RUN397_PROGRESS.json"):
            raw = (self.source / name).read_bytes()
            self.fixture.manifest["copied"][name] = {
                "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        self.report.update({
            "run": "Run421", "status": "STAGE4_NATIVE_PARTIAL_NO_PROMOTION",
            "rows_verified": 168, "completed": list(stage.PREFIX),
            "remaining_arms": 5,
            "native_execute_requested": True,
            "native_execute_attempted": True,
            "native_execution_performed": True,
            "progress_sha256": stage.safe.sha_file(progress_path)})
        self.report["safe_export"]["copied_files"] = len(self.fixture.manifest["copied"])
        self.report["safe_export"]["copied_bytes"] = sum(
            x["bytes"] for x in self.fixture.manifest["copied"].values())
        self.fixture.seal()

    def audit(self):
        return mock.patch.object(stage.audit, "verify", return_value={
            "status": "RUN429_NATIVE_168_INDEPENDENTLY_VERIFIED"})

    def installed(self):
        path = self.root / "installed"
        (path / "bin").mkdir(parents=True, exist_ok=True)
        (path / "bin/llama-server").write_bytes(b"synthetic")
        return path

    def sha_for_runner(self):
        original = stage.safe.sha_file
        def selective(path):
            if Path(path).name == "llama-server":
                return stage.RUN401_EXECUTABLE_SHA256
            return original(path)
        return selective

    def test_source_only_restores_168_without_native(self):
        with self.audit(), mock.patch.object(stage.resume, "run") as native:
            report = stage.stage5(self.source, self.report, self.root / "work")
        native.assert_not_called()
        self.assertEqual(report["status"], "STAGE5_READY_NO_NATIVE")
        self.assertEqual(report["rows_verified"], 168)
        self.assertEqual(report["completed"], list(stage.PREFIX))
        self.assertFalse(report["native_execute_attempted"])
        self.assertFalse(report["canonical_gate_pass"])
        self.assertFalse((self.root / "work" / stage.gate.MANIFEST).exists())

    def test_execute_requires_installed_home_and_export(self):
        report = stage.stage5(self.source, self.report, self.root / "work",
                              execute=True)
        self.assertEqual(report["status"], "STAGE5_RED_PRESERVED")
        self.assertFalse((self.root / "work").exists())
        self.assertIn("INSTALLED_HOME_AND_SAFE_EXPORT_REQUIRED_FOR_EXECUTE",
                      report["errors"])

    def test_prior_receipt_mismatch_blocks_native(self):
        installed = self.installed()
        with self.audit(), mock.patch.object(stage.safe, "sha_file",
                                             side_effect=self.sha_for_runner()), \
             mock.patch.object(stage.resume, "validate_completed",
                               side_effect=ValueError("MODEL_IDENTITY_CHANGED")), \
             mock.patch.object(stage.resume, "run") as native, \
             mock.patch.object(stage.safe, "export", return_value={
                 "status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS", "errors": []}):
            report = stage.stage5(self.source, self.report, self.root / "work",
                                  installed=installed, execute=True,
                                  export_dest=self.root / "out")
        native.assert_not_called()
        self.assertEqual(report["status"], "STAGE5_RED_PRESERVED")
        self.assertFalse(report["native_execute_attempted"])
        self.assertIn("MODEL_IDENTITY_CHANGED", str(report["errors"]))

    def test_exact_one_p21_produces_only_synthetic_210_no_promotion(self):
        installed = self.installed()
        progress = json.loads((self.source / "RUN397_PROGRESS.json").read_text())
        progress["completed"]["P_s21"] = {
            "attempt": "attempts/P_s21/attempt-0001", "validated": self.receipt}
        result = {"status": "INCOMPLETE", "completed": progress["completed"],
                  "failures_preserved": {}, "canonical_gate_pass": False,
                  "step2_exit": "UTILITY_FAIL"}
        def synthetic_native(work, *args, **kwargs):
            root = Path(work)
            (root / "RUN397_PROGRESS.json").write_text(json.dumps(progress))
            (root / "attempts/P_s21/attempt-0001").mkdir(parents=True)
            return result
        with self.audit(), mock.patch.object(stage.safe, "sha_file",
                                             side_effect=self.sha_for_runner()), \
             mock.patch.object(stage.resume, "validate_completed",
                               return_value=self.receipt), \
             mock.patch.object(stage.resume, "run",
                               side_effect=synthetic_native) as called, \
             mock.patch.object(stage.safe, "export", return_value={
                 "status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS", "errors": []}):
            report = stage.stage5(self.source, self.report, self.root / "work",
                                  installed=installed, execute=True,
                                  export_dest=self.root / "out")
        called.assert_called_once()
        self.assertEqual(called.call_args.kwargs["max_new_arms"], 1)
        self.assertFalse(called.call_args.kwargs["pilot"])
        self.assertEqual(report["status"], "STAGE5_NATIVE_PARTIAL_NO_PROMOTION")
        self.assertEqual(report["rows_verified"], 210)
        self.assertEqual(report["remaining_arms"], 4)
        self.assertEqual(report["completed"][-1], "P_s21")
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_exit"], "UTILITY_FAIL")

    def test_wrong_next_arm_refused(self):
        installed = self.installed()
        progress = json.loads((self.source / "RUN397_PROGRESS.json").read_text())
        progress["completed"]["S_s21"] = {
            "attempt": "attempts/S_s21/attempt-0001", "validated": self.receipt}
        result = {"status": "INCOMPLETE", "completed": progress["completed"],
                  "failures_preserved": {}, "canonical_gate_pass": False,
                  "step2_exit": "UTILITY_FAIL"}
        with self.audit(), mock.patch.object(stage.safe, "sha_file",
                                             side_effect=self.sha_for_runner()), \
             mock.patch.object(stage.resume, "validate_completed",
                               return_value=self.receipt), \
             mock.patch.object(stage.resume, "run", return_value=result), \
             mock.patch.object(stage.safe, "export", return_value={
                 "status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS", "errors": []}):
            report = stage.stage5(self.source, self.report, self.root / "work",
                                  installed=installed, execute=True,
                                  export_dest=self.root / "out")
        self.assertEqual(report["status"], "STAGE5_RED_PRESERVED")
        self.assertIn("STAGE5_NEXT_ARM_NOT_COMPLETE", str(report["errors"]))

    def test_tampered_safe_export_bytes_rejected_before_work(self):
        (self.source / "attempts/O_s21/attempt-0001/native.json").write_bytes(b"bad")
        with self.audit(), mock.patch.object(stage.resume, "run") as native:
            report = stage.stage5(self.source, self.report, self.root / "work")
        native.assert_not_called()
        self.assertEqual(report["status"], "STAGE5_RED_PRESERVED")
        self.assertFalse((self.root / "work").exists())


if __name__ == "__main__":
    unittest.main()
