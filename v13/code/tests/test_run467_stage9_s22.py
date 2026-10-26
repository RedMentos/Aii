"""Run467 final S_s22 stage9 source-only preview and fail-closed gates."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run467_stage9_s22 as stage


class Run467Stage9Tests(unittest.TestCase):
    def imported(self):
        return {"status": "RUN466_NATIVE336_IMPORTED_VERIFIED",
                "rows_verified": 336, "canonical_gate_pass": False,
                "step2_exit": "UTILITY_FAIL"}

    def preflight(self):
        return {"status": "STAGE9_PREVIOUS_336_ROWS_VERIFIED",
                "completed": list(stage.PREFIX), "rows_verified": 336,
                "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}

    def call(self, execute=False, imported=None, preflight=None,
             installed=None, export=None):
        with (patch.object(stage.stage8_import, "import_stage8",
                           return_value=self.imported() if imported is None
                           else imported) as import_call,
              patch.object(stage, "verify_previous",
                           return_value=self.preflight() if preflight is None
                           else preflight),
              patch.object(stage.resume, "run",
                           side_effect=AssertionError("NO_NATIVE_IN_SOURCE_TEST")) as native):
            result = stage.stage9(
                "unavailable.zip", "0" * 64, {}, "/no-model-work",
                installed=installed, execute=execute, export_dest=export)
            return result, import_call, native

    def test_exact_final_arm_is_s_seed22(self):
        self.assertEqual(stage.NEXT, "S_s22")
        self.assertEqual(stage.ALL,
                         ("O_s20", "P_s20", "S_s20", "O_s21",
                          "P_s21", "S_s21", "O_s22", "P_s22", "S_s22"))
        self.assertEqual(len(stage.ALL) * 42, 378)

    def test_default_preview_requires_prior_import_and_no_native(self):
        result, imported, native = self.call()
        self.assertEqual(result["status"], "STAGE9_READY_NO_NATIVE")
        self.assertEqual(result["rows_verified"], 336)
        self.assertEqual(result["remaining_arms"], 1)
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
        self.assertEqual(result["status"], "STAGE9_RED_PRESERVED")
        self.assertIn("INSTALLED_HOME_AND_SAFE_EXPORT_REQUIRED_FOR_EXECUTE",
                      result["errors"])
        imported.assert_not_called()
        native.assert_not_called()

    def test_bad_eight_receipt_import_refuses_native(self):
        bad = dict(self.imported(), status="RUN466_NATIVE336_IMPORT_RED_PRESERVED")
        result, imported, native = self.call(imported=bad)
        self.assertEqual(result["status"], "STAGE9_RED_PRESERVED")
        self.assertIn("STAGE9_336_IMPORT_NOT_VERIFIED", result["errors"][0])
        native.assert_not_called()

    def test_previous_receipt_refusal_preserves_red(self):
        with (patch.object(stage.stage8_import, "import_stage8",
                           return_value=self.imported()),
              patch.object(stage, "verify_previous",
                           side_effect=ValueError("RECEIPT_CHANGED")),
              patch.object(stage.resume, "run") as native):
            result = stage.stage9("missing.zip", "0" * 64, {}, "/no-work")
        self.assertEqual(result["status"], "STAGE9_RED_PRESERVED")
        self.assertIn("RECEIPT_CHANGED", result["errors"][0])
        native.assert_not_called()

    def test_forged_preflight_success_is_refused(self):
        bad = dict(self.preflight(), rows_verified=378)
        result, imported, native = self.call(preflight=bad)
        self.assertEqual(result["status"], "STAGE9_RED_PRESERVED")
        self.assertIn("STAGE9_PREFLIGHT_NOT_VERIFIED", result["errors"][0])
        native.assert_not_called()

    def test_synthetic_final_structural_status_still_never_promotes_step2(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "work"
            work.mkdir()
            frozen = stage.r394.manifest(stage.r394.FIXTURES, False,
                                          list(stage.r394.ARMS), list(stage.r394.SEEDS))
            (work / "RUN394_PREREGISTERED_FIXTURES.json").write_text(json.dumps(frozen))
            completed = {
                rid: {"attempt": f"attempts/{rid}/attempt-0001",
                      "validated": {"rows": 42}}
                for rid in stage.ALL}
            simulated = {"status": "ALL_ARMS_STRUCTURALLY_RECORDED",
                         "completed": completed, "failures_preserved": {},
                         "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}
            with (patch.object(stage.stage8_import, "import_stage8",
                               return_value=self.imported()),
                  patch.object(stage, "verify_previous",
                               return_value=self.preflight()),
                  patch.object(stage.safe, "sha_file",
                               return_value=stage.RUN401_EXECUTABLE_SHA256),
                  patch.object(stage.resume, "run", return_value=simulated),
                  patch.object(stage.resume, "validate_completed",
                               return_value={"rows": 42}),
                  patch.object(stage.safe, "export",
                               return_value={"status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS",
                                             "errors": []})):
                result = stage.stage9("synthetic.zip", "0" * 64, {}, work,
                                      installed="/synthetic-installed", execute=True,
                                      export_dest="/synthetic-export")
        self.assertEqual(result["status"], "STAGE9_NATIVE_378_STRUCTURAL_NO_PROMOTION")
        self.assertEqual(result["rows_verified"], 378)
        self.assertEqual(result["remaining_arms"], 0)
        self.assertTrue(result["native_execution_performed"])
        self.assertFalse(result["canonical_gate_pass"])
        self.assertEqual(result["step2_exit"], "UTILITY_FAIL")
        self.assertFalse(result["redmi_measured"])
        self.assertEqual(result["jepa_weight"], 0)

    def test_native_exception_remains_red_and_safe_export_is_attempted(self):
        with (patch.object(stage.stage8_import, "import_stage8",
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
            result = stage.stage9("missing.zip", "0" * 64, {}, "/no-work",
                                  installed="/no-model", execute=True,
                                  export_dest="/no-export")
        self.assertEqual(result["status"], "STAGE9_RED_PRESERVED")
        self.assertTrue(result["native_execute_attempted"])
        self.assertFalse(result["native_execution_performed"])
        self.assertIn("NATIVE_NOT_AVAILABLE", result["errors"][0])
        native.assert_called_once()
        export.assert_called_once()

    def test_safe_export_failure_does_not_promote(self):
        with (patch.object(stage.stage8_import, "import_stage8",
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
            result = stage.stage9("missing.zip", "0" * 64, {}, "/no-work",
                                  installed="/no-model", execute=True,
                                  export_dest="/no-export")
        self.assertEqual(result["status"], "STAGE9_RED_PRESERVED")
        self.assertTrue(any("SAFE_EXPORT_RED" in x for x in result["errors"]))
        self.assertFalse(result["canonical_gate_pass"])


if __name__ == "__main__":
    unittest.main()
