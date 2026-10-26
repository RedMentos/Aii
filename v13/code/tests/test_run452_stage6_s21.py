"""Run452 synthetic controls: exact next S_s21, fail closed, no native in preview.

The separate CI also imports the actual original Run437 210-row artifact and
checks five real Linux-native receipts; these mocks are only control tests.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run452_stage6_s21 as stage


def imported():
    return {"status": "RUN438_STAGE5_ARTIFACT_IMPORTED_VERIFIED",
            "rows_verified": 210, "canonical_gate_pass": False}


def prior():
    return {"status": "STAGE6_PREVIOUS_210_ROWS_VERIFIED",
            "rows_verified": 210, "canonical_gate_pass": False,
            "step2_exit": "UTILITY_FAIL"}


class Run452Stage6Controls(unittest.TestCase):
    def test_source_only_preview_never_calls_native_or_exports(self):
        with patch.object(stage.stage5_import, "import_stage5", return_value=imported()), \
             patch.object(stage, "verify_previous", return_value=prior()), \
             patch.object(stage.resume, "run", side_effect=AssertionError("NATIVE_FORBIDDEN")), \
             patch.object(stage.safe, "export", side_effect=AssertionError("EXPORT_FORBIDDEN")):
            r = stage.stage6("archive", "sha", {}, "work")
        self.assertEqual(r["status"], "STAGE6_READY_NO_NATIVE")
        self.assertEqual(r["rows_verified"], 210)
        self.assertEqual(r["completed"], list(stage.PREFIX))
        self.assertEqual(r["remaining_arms"], 4)
        self.assertFalse(r["native_execute_attempted"])
        self.assertFalse(r["native_execution_performed"])
        self.assertFalse(r["canonical_gate_pass"])

    def test_execute_requires_installed_home_and_safe_export_before_import(self):
        with patch.object(stage.stage5_import, "import_stage5",
                          side_effect=AssertionError("IMPORT_FORBIDDEN")):
            r = stage.stage6("archive", "sha", {}, "work", execute=True)
        self.assertEqual(r["status"], "STAGE6_RED_PRESERVED")
        self.assertIn("INSTALLED_HOME_AND_SAFE_EXPORT_REQUIRED_FOR_EXECUTE", r["errors"])
        self.assertFalse(r["native_execute_attempted"])

    def test_bad_import_and_prior_receipt_never_start_native(self):
        with patch.object(stage.stage5_import, "import_stage5",
                          side_effect=ValueError("ARTIFACT_SHA_MISMATCH")), \
             patch.object(stage.resume, "run", side_effect=AssertionError("NATIVE_FORBIDDEN")):
            r = stage.stage6("archive", "sha", {}, "work")
        self.assertEqual(r["status"], "STAGE6_RED_PRESERVED")
        self.assertIn("ARTIFACT_SHA_MISMATCH", " ".join(r["errors"]))
        with patch.object(stage.stage5_import, "import_stage5", return_value=imported()), \
             patch.object(stage, "verify_previous", side_effect=ValueError("RECEIPT_RED")), \
             patch.object(stage.resume, "run", side_effect=AssertionError("NATIVE_FORBIDDEN")):
            r = stage.stage6("archive", "sha", {}, "work")
        self.assertEqual(r["status"], "STAGE6_RED_PRESERVED")
        self.assertIn("RECEIPT_RED", " ".join(r["errors"]))

    def test_wrong_next_arm_is_red_and_preserves_safe_export(self):
        fake = {"status": "INCOMPLETE", "completed": {k: {} for k in stage.PREFIX},
                "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
                "failures_preserved": {}}
        with patch.object(stage.stage5_import, "import_stage5", return_value=imported()), \
             patch.object(stage, "verify_previous", return_value=prior()), \
             patch.object(stage.safe, "sha_file", return_value=stage.RUN401_EXECUTABLE_SHA256), \
             patch.object(stage.resume, "run", return_value=fake) as native, \
             patch.object(stage.safe, "export", return_value={
                 "status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS"}) as exporter:
            r = stage.stage6("archive", "sha", {}, "work",
                             installed="installed", execute=True, export_dest="safe-out")
        native.assert_called_once()
        exporter.assert_called_once()
        self.assertEqual(r["status"], "STAGE6_RED_PRESERVED")
        self.assertTrue(r["native_execute_attempted"])
        self.assertFalse(r["native_execution_performed"])
        self.assertIn("STAGE6_NEXT_ARM_NOT_COMPLETE", " ".join(r["errors"]))
        self.assertEqual(r["step2_exit"], "UTILITY_FAIL")

    def test_wrong_runner_refuses_before_native_and_preserves_export(self):
        with patch.object(stage.stage5_import, "import_stage5", return_value=imported()), \
             patch.object(stage, "verify_previous", return_value=prior()), \
             patch.object(stage.safe, "sha_file", return_value="0" * 64), \
             patch.object(stage.resume, "run", side_effect=AssertionError("NATIVE_FORBIDDEN")), \
             patch.object(stage.safe, "export", return_value={
                 "status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS"}):
            r = stage.stage6("archive", "sha", {}, "work",
                             installed="installed", execute=True, export_dest="safe-out")
        self.assertEqual(r["status"], "STAGE6_RED_PRESERVED")
        self.assertFalse(r["native_execute_attempted"])
        self.assertIn("INSTALLED_RUNNER_SHA_MISMATCH", " ".join(r["errors"]))


if __name__ == "__main__":
    unittest.main()
