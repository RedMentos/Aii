"""Run462 next P_s22 stage8 source-only preview and fail-closed gates."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run462_stage8_p22 as stage


class Run462Stage8Tests(unittest.TestCase):
    def imported(self):
        return {"status": "RUN461_NATIVE294_IMPORTED_VERIFIED",
                "rows_verified": 294, "canonical_gate_pass": False,
                "step2_exit": "UTILITY_FAIL"}

    def preflight(self):
        return {"status": "STAGE8_PREVIOUS_294_ROWS_VERIFIED",
                "completed": list(stage.PREFIX), "rows_verified": 294,
                "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}

    def call(self, execute=False, imported=None, preflight=None,
             installed=None, export=None):
        with (patch.object(stage.stage7_import, "import_stage7",
                           return_value=self.imported() if imported is None
                           else imported) as import_call,
              patch.object(stage, "verify_previous",
                           return_value=self.preflight() if preflight is None
                           else preflight),
              patch.object(stage.resume, "run",
                           side_effect=AssertionError("NO_NATIVE_IN_SOURCE_TEST")) as native):
            result = stage.stage8(
                "unavailable.zip", "0" * 64, {}, "/no-model-work",
                installed=installed, execute=execute, export_dest=export)
            return result, import_call, native

    def test_exact_eighth_arm_is_p_seed22(self):
        self.assertEqual(stage.NEXT, "P_s22")
        self.assertEqual(stage.ALL,
                         ("O_s20", "P_s20", "S_s20", "O_s21",
                          "P_s21", "S_s21", "O_s22", "P_s22"))
        self.assertEqual(len(stage.ALL) * 42, 336)

    def test_default_preview_requires_prior_import_and_no_native(self):
        result, imported, native = self.call()
        self.assertEqual(result["status"], "STAGE8_READY_NO_NATIVE")
        self.assertEqual(result["rows_verified"], 294)
        self.assertEqual(result["remaining_arms"], 2)
        self.assertEqual(result["completed"], list(stage.PREFIX))
        self.assertFalse(result["native_execute_attempted"])
        self.assertFalse(result["native_execution_performed"])
        self.assertFalse(result["canonical_gate_pass"])
        self.assertEqual(result["step2_exit"], "UTILITY_FAIL")
        self.assertFalse(result["redmi_measured"])
        self.assertEqual(result["jepa_weight"], 0)
        imported.assert_called_once()
        native.assert_not_called()

    def test_execute_without_exact_prerequisites_refuses_before_import(self):
        result, imported, native = self.call(execute=True)
        self.assertEqual(result["status"], "STAGE8_RED_PRESERVED")
        self.assertIn("INSTALLED_HOME_AND_SAFE_EXPORT_REQUIRED_FOR_EXECUTE",
                      result["errors"])
        imported.assert_not_called()
        native.assert_not_called()

    def test_bad_seven_receipt_import_refuses_native(self):
        bad = dict(self.imported(), status="RUN461_NATIVE294_IMPORT_RED_PRESERVED")
        result, imported, native = self.call(imported=bad)
        self.assertEqual(result["status"], "STAGE8_RED_PRESERVED")
        self.assertIn("STAGE8_294_IMPORT_NOT_VERIFIED", result["errors"][0])
        native.assert_not_called()

    def test_previous_receipt_refusal_preserves_red(self):
        with (patch.object(stage.stage7_import, "import_stage7",
                           return_value=self.imported()),
              patch.object(stage, "verify_previous",
                           side_effect=ValueError("RECEIPT_CHANGED")),
              patch.object(stage.resume, "run") as native):
            result = stage.stage8("missing.zip", "0" * 64, {}, "/no-work")
        self.assertEqual(result["status"], "STAGE8_RED_PRESERVED")
        self.assertIn("RECEIPT_CHANGED", result["errors"][0])
        native.assert_not_called()

    def test_forged_preflight_success_is_refused(self):
        bad = dict(self.preflight(), rows_verified=336)
        result, imported, native = self.call(preflight=bad)
        self.assertEqual(result["status"], "STAGE8_RED_PRESERVED")
        self.assertIn("STAGE8_PREFLIGHT_NOT_VERIFIED", result["errors"][0])
        native.assert_not_called()

    def test_native_exception_remains_red_and_safe_export_is_attempted(self):
        with (patch.object(stage.stage7_import, "import_stage7",
                           return_value=self.imported()),
              patch.object(stage, "verify_previous",
                           return_value=self.preflight()),
              patch.object(stage.safe, "sha_file",
                           return_value=stage.RUN401_EXECUTABLE_SHA256),
              patch.object(stage.resume, "run",
                           side_effect=ValueError("NATIVE_NOT_AVAILABLE")) as native,
              patch.object(stage.safe, "export",
                           return_value={"status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS",
                                         "errors": []}) as export):
            result = stage.stage8("missing.zip", "0" * 64, {}, "/no-work",
                                  installed="/no-model", execute=True,
                                  export_dest="/no-export")
        self.assertEqual(result["status"], "STAGE8_RED_PRESERVED")
        self.assertTrue(result["native_execute_attempted"])
        self.assertFalse(result["native_execution_performed"])
        self.assertIn("NATIVE_NOT_AVAILABLE", result["errors"][0])
        native.assert_called_once()
        export.assert_called_once()

    def test_safe_export_failure_does_not_promote(self):
        with (patch.object(stage.stage7_import, "import_stage7",
                           return_value=self.imported()),
              patch.object(stage, "verify_previous",
                           return_value=self.preflight()),
              patch.object(stage.safe, "sha_file",
                           return_value=stage.RUN401_EXECUTABLE_SHA256),
              patch.object(stage.resume, "run",
                           side_effect=ValueError("NATIVE_RED")),
              patch.object(stage.safe, "export",
                           return_value={"status": "EXPORT_RED",
                                         "errors": ["HASH_MISMATCH"]})):
            result = stage.stage8("missing.zip", "0" * 64, {}, "/no-work",
                                  installed="/no-model", execute=True,
                                  export_dest="/no-export")
        self.assertEqual(result["status"], "STAGE8_RED_PRESERVED")
        self.assertTrue(any("SAFE_EXPORT_RED" in x for x in result["errors"]))
        self.assertFalse(result["canonical_gate_pass"])


if __name__ == "__main__":
    unittest.main()
