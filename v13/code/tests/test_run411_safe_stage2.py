"""Run411 source-only orchestration controls; no real model inference in these tests."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run411_safe_stage2 as m


class Run411Stage2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / "work"
        self.installed = self.root / "installed"
        self.export_dest = self.root / "export"
        self.archive = self.root / "original.zip"
        self.sha = "a" * 64
        self.stage1 = {
            "status": "FILTERED_STAGE1_VERIFIED_NO_PROMOTION",
            "original_zip_sha256": self.sha, "members_verified": 107,
            "omitted_registered_models": [{"path": "synthetic/model.gguf"}],
            "unlisted_binary_hashes": {}, "all_member_sha_checked": True,
            "zip_crc_checked": True}
        self.first = {"attempt": "attempts/O_s20/attempt-0001",
                      "validated": {"rows": 42}}
        self.out = {"status": "INCOMPLETE",
                    "completed": {"O_s20": self.first,
                                  "P_s20": {"attempt": "attempts/P_s20/attempt-0001",
                                            "validated": {"rows": 42}}},
                    "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
                    "failures_preserved": {}}
        self.safe = {"status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS",
                     "manifest_sha256": "b" * 64, "errors": []}
        self.patchers = [
            mock.patch.object(m.filtered, "audit_or_restore", return_value=self.stage1),
            mock.patch.object(m, "load", return_value={"stage": "FULL"}),
            mock.patch.object(m, "catalog", return_value={
                "runner": {"linux_binaries": {"linux-x86_64": {"sha256": "c" * 64}}}}),
            mock.patch.object(m.resume, "previous_success", return_value=(self.first, [])),
            mock.patch.object(m.resume, "run", return_value=self.out),
            mock.patch.object(m.resume, "validate_completed", return_value={"rows": 42}),
            mock.patch.object(m, "sha", return_value="d" * 64),
            mock.patch.object(m.safe, "export", return_value=self.safe),
        ]
        self.mocks = [p.start() for p in self.patchers]
        self.mocks[6].side_effect = lambda p: (m.RUN401_EXECUTABLE_SHA256
            if Path(p).name == "llama-server" else "d" * 64)
        self.addCleanup(lambda: [p.stop() for p in reversed(self.patchers)])

    def run_stage(self, execute=False, installed=None, export_dest=None):
        return m.stage2(self.archive, self.sha, self.work, installed, execute, export_dest)

    def test_preview_restores_and_checks_stage1_without_native(self):
        result = self.run_stage()
        self.assertEqual(result["status"], "STAGE2_READY_NO_NATIVE")
        self.assertEqual(result["rows_verified"], 42)
        self.assertEqual(result["remaining_arms"], 8)
        self.assertFalse(result["native_execute_attempted"])
        self.assertFalse(result["canonical_gate_pass"])
        self.mocks[4].assert_not_called()
        self.mocks[7].assert_not_called()

    def test_explicit_execute_requires_installed_and_export(self):
        result = self.run_stage(execute=True, installed=self.installed)
        self.assertEqual(result["status"], "STAGE2_RED_PRESERVED")
        self.assertIn("INSTALLED_HOME_AND_SAFE_EXPORT_REQUIRED_FOR_EXECUTE", result["errors"])
        self.mocks[0].assert_not_called()
        self.mocks[4].assert_not_called()

    def test_invalid_stage1_never_starts_native(self):
        self.mocks[0].return_value = {"status": "FILTERED_STAGE1_RED_PRESERVED",
                                      "errors": ["ZIP_SHA_MISMATCH"]}
        result = self.run_stage(execute=True, installed=self.installed,
                                export_dest=self.export_dest)
        self.assertEqual(result["status"], "STAGE2_RED_PRESERVED")
        self.assertFalse(result["native_execute_attempted"])
        self.mocks[4].assert_not_called()
        self.mocks[7].assert_not_called()

    def test_invalid_stage1_receipt_never_starts_native(self):
        self.mocks[3].return_value = (None, [{"reason": "FAILED_RAW"}])
        result = self.run_stage(execute=True, installed=self.installed,
                                export_dest=self.export_dest)
        self.assertEqual(result["status"], "STAGE2_RED_PRESERVED")
        self.assertFalse(result["native_execute_attempted"])
        self.mocks[4].assert_not_called()
        self.mocks[7].assert_called_once()

    def test_exactly_one_new_native_arm_and_safe_export(self):
        result = self.run_stage(execute=True, installed=self.installed,
                                export_dest=self.export_dest)
        self.assertEqual(result["status"], "STAGE2_NATIVE_PARTIAL_NO_PROMOTION")
        self.assertTrue(result["native_execute_attempted"])
        self.assertTrue(result["native_execution_performed"])
        self.assertEqual(result["rows_verified"], 84)
        self.assertEqual(result["remaining_arms"], 7)
        self.assertEqual(result["completed"], ["O_s20", "P_s20"])
        self.assertFalse(result["canonical_gate_pass"])
        self.mocks[4].assert_called_once_with(self.work, self.installed,
                                               pilot=False, execute=True, max_new_arms=1)
        self.assertEqual(self.mocks[5].call_count, 2)
        self.mocks[7].assert_called_once_with(self.work, self.installed, self.export_dest)

    def test_mismatched_installed_executable_blocks_native_and_exports(self):
        self.mocks[6].side_effect = None
        self.mocks[6].return_value = "0" * 64
        result = self.run_stage(execute=True, installed=self.installed,
                                export_dest=self.export_dest)
        self.assertEqual(result["status"], "STAGE2_RED_PRESERVED")
        self.assertIn("INSTALLED_RUNNER_EXECUTABLE_SHA_MISMATCH", str(result["errors"]))
        self.assertFalse(result["native_execute_attempted"])
        self.mocks[4].assert_not_called()
        self.mocks[7].assert_called_once()

    def test_native_failure_preserves_red_and_still_exports(self):
        self.mocks[4].side_effect = ValueError("SYNTHETIC_NATIVE_FAILURE")
        result = self.run_stage(execute=True, installed=self.installed,
                                export_dest=self.export_dest)
        self.assertEqual(result["status"], "STAGE2_RED_PRESERVED")
        self.assertTrue(result["native_execute_attempted"])
        self.assertFalse(result["native_execution_performed"])
        self.assertIn("SYNTHETIC_NATIVE_FAILURE", str(result["errors"]))
        self.mocks[7].assert_called_once()

    def test_failed_safe_export_cannot_promote_native_success(self):
        self.mocks[7].return_value = {"status": "EXPORT_RED_PRESERVED",
                                      "errors": ["MODEL_OR_MANIFEST_FILE_IN_WORK"]}
        result = self.run_stage(execute=True, installed=self.installed,
                                export_dest=self.export_dest)
        self.assertEqual(result["status"], "STAGE2_RED_PRESERVED")
        self.assertIn("SAFE_EXPORT_RED", str(result["errors"]))
        self.assertFalse(result["canonical_gate_pass"])

    def test_incomplete_second_arm_remains_red_but_exports(self):
        self.out["completed"].pop("P_s20")
        result = self.run_stage(execute=True, installed=self.installed,
                                export_dest=self.export_dest)
        self.assertEqual(result["status"], "STAGE2_RED_PRESERVED")
        self.assertIn("STAGE2_NEXT_ARM_NOT_COMPLETE", str(result["errors"]))
        self.mocks[7].assert_called_once()


    def test_native_receipt_runner_sha_is_observed_executable_not_release_tar(self):
        result = self.run_stage()
        self.assertEqual(result["status"], "STAGE2_READY_NO_NATIVE")
        observed = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
        self.assertEqual(self.mocks[3].call_args.kwargs["current_runner_sha"], observed)
        self.assertNotEqual(observed, "c" * 64)


if __name__ == "__main__":
    unittest.main()
