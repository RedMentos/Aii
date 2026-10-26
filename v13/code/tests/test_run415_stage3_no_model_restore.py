"""Run415 adversarial synthetic no-model stage3 restore; never executes native."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run415_stage3_no_model_restore as stage
import run413_export_receipt_gate as gate


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class Run415Stage3RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        progress = {"canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
                    "completed": {a + "_s20": {
                        "attempt": "attempts/" + a + "_s20/attempt-0001",
                        "validated": {"rows": 42}
                    } for a in ("O", "P")}, "failures_preserved": {}}
        files = {
            "RUN397_PROGRESS.json": json.dumps(progress).encode(),
            "RUN394_PREREGISTERED_FIXTURES.json": json.dumps(
                stage.r394.manifest(stage.r394.FIXTURES, False,
                                    list(stage.r394.ARMS),
                                    list(stage.r394.SEEDS)),
                sort_keys=True).encode(),
            "RUN397_OWNER.lock": b"",
            "attempts/O_s20/attempt-0001/native.json": b'{"raw":true}',
            "attempts/P_s20/attempt-0001/native.json": b'{"raw":true}',
        }
        copied = {}
        for name, raw in files.items():
            p = self.source / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
            copied[name] = {"sha256": sha(raw), "bytes": len(raw)}
        directories = [".", "attempts", "attempts/O_s20", "attempts/P_s20",
                       "attempts/O_s20/attempt-0001", "attempts/P_s20/attempt-0001"]
        self.manifest = {
            "schema": "RUN409_SAFE_NATIVE_EXPORT_V1", "source_run": "Run397",
            "copied": copied, "directories": directories,
            "omitted_installed_symlinks": [
                "attempts/P_s20/attempt-0001/P_s20-home/models"],
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}
        self.report = {
            "run": "Run411", "status": "STAGE2_NATIVE_PARTIAL_NO_PROMOTION",
            "errors": [], "native_execute_requested": True,
            "native_execute_attempted": True, "native_execution_performed": True,
            "rows_verified": 84, "completed": ["O_s20", "P_s20"],
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
            "redmi_measured": False, "jepa_weight": 0,
            "safe_export": {"status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS",
                            "errors": [], "copied_files": len(copied),
                            "copied_bytes": sum(v["bytes"] for v in copied.values())}}
        self.reseal()

    def reseal(self):
        (self.source / gate.MANIFEST).write_text(json.dumps(self.manifest, sort_keys=True))
        self.report["safe_export"]["manifest_sha256"] = stage.safe.sha_file(
            self.source / gate.MANIFEST)

    def test_atomic_ready_restore_preserves_all_receipts_without_manifest(self):
        dest = self.root / "work"
        result = stage.stage3(self.source, self.report, dest)
        self.assertEqual(result["status"], "STAGE3_READY_NO_NATIVE")
        self.assertEqual(result["rows_verified"], 84)
        self.assertFalse(result["native_execution_performed"])
        self.assertFalse(result["canonical_gate_pass"])
        self.assertTrue((dest / "attempts/P_s20/attempt-0001/native.json").is_file())
        self.assertFalse((dest / gate.MANIFEST).exists())
        self.assertEqual(stage.safe.sha_file(dest / "RUN397_PROGRESS.json"),
                         stage.safe.sha_file(self.source / "RUN397_PROGRESS.json"))
        self.assertTrue((dest / "RUN397_OWNER.lock").is_file())

    def test_tampered_source_is_red_and_destination_absent(self):
        (self.source / "RUN397_PROGRESS.json").write_text("tampered")
        dest = self.root / "work"
        result = stage.stage3(self.source, self.report, dest)
        self.assertEqual(result["status"], "STAGE3_RED_PRESERVED")
        self.assertFalse(dest.exists())
        self.assertIn("EXPORT_FILE_METADATA_INVALID", str(result["errors"]))

    def test_unlisted_source_file_is_red(self):
        (self.source / "unlisted.txt").write_text("unregistered")
        dest = self.root / "work"
        result = stage.stage3(self.source, self.report, dest)
        self.assertEqual(result["status"], "STAGE3_RED_PRESERVED")
        self.assertFalse(dest.exists())
        self.assertIn("UNLISTED_EXPORT_FILE", str(result["errors"]))

    def test_symlink_source_is_red(self):
        (self.source / "extra-link").symlink_to(self.source, target_is_directory=True)
        result = stage.stage3(self.source, self.report, self.root / "work")
        self.assertEqual(result["status"], "STAGE3_RED_PRESERVED")
        self.assertIn("EXPORT_SYMLINK_DIRECTORY", str(result["errors"]))

    def test_unverified_run413_native_red_cannot_restore(self):
        self.report["status"] = "STAGE2_RED_PRESERVED"
        result = stage.stage3(self.source, self.report, self.root / "work")
        self.assertEqual(result["status"], "STAGE3_RED_PRESERVED")
        self.assertFalse((self.root / "work").exists())

    def test_execute_requires_installed_and_safe_export(self):
        result = stage.stage3(self.source, self.report, self.root / "work", execute=True)
        self.assertEqual(result["status"], "STAGE3_RED_PRESERVED")
        self.assertIn("INSTALLED_HOME_AND_SAFE_EXPORT_REQUIRED_FOR_EXECUTE", result["errors"])
        self.assertFalse((self.root / "work").exists())

    def test_second_restore_never_overwrites_original(self):
        dest = self.root / "work"
        first = stage.stage3(self.source, self.report, dest)
        self.assertEqual(first["status"], "STAGE3_READY_NO_NATIVE")
        second = stage.stage3(self.source, self.report, dest)
        self.assertEqual(second["status"], "STAGE3_RED_PRESERVED")
        self.assertIn("DESTINATION_NOT_FRESH", str(second["errors"]))
        self.assertTrue((dest / "RUN397_PROGRESS.json").is_file())

    def test_synthetic_native_success_126_rows_is_not_gate_promotion(self):
        installed = self.root / "installed"
        (installed / "bin").mkdir(parents=True)
        (installed / "bin/llama-server").write_bytes(b"fake, never executed")
        receipts = {a + "_s20": {"attempt": "attempts/" + a + "_s20/attempt-0001",
                                 "validated": {"rows": 42}} for a in ("O", "P", "S")}
        result = {"status": "INCOMPLETE", "completed": receipts,
                  "failures_preserved": {}, "canonical_gate_pass": False,
                  "step2_exit": "UTILITY_FAIL"}
        original_sha_file = stage.safe.sha_file
        def selective_sha(path):
            if Path(path).name == "llama-server":
                return stage.RUN401_EXECUTABLE_SHA256
            return original_sha_file(path)
        with mock.patch.object(stage.safe, "sha_file",
                               side_effect=selective_sha), \
             mock.patch.object(stage.resume, "run", return_value=result) as native, \
             mock.patch.object(stage.resume, "validate_completed",
                               return_value={"rows": 42}), \
             mock.patch.object(stage.safe, "export",
                               return_value={"status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS",
                                             "errors": []}):
            report = stage.stage3(self.source, self.report, self.root / "work",
                                  installed=installed, execute=True,
                                  export_dest=self.root / "out")
        self.assertEqual(native.call_count, 1)
        self.assertEqual(report["status"], "STAGE3_NATIVE_PARTIAL_NO_PROMOTION")
        self.assertEqual(report["rows_verified"], 126)
        self.assertFalse(report["canonical_gate_pass"])
        self.assertFalse(report["redmi_measured"])

    def test_unverified_restored_receipt_blocks_native_before_launch(self):
        installed = self.root / "installed"
        (installed / "bin").mkdir(parents=True)
        (installed / "bin/llama-server").write_bytes(b"synthetic only")
        original_sha = stage.safe.sha_file

        def selective_sha(path):
            if Path(path).name == "llama-server":
                return stage.RUN401_EXECUTABLE_SHA256
            return original_sha(path)

        with mock.patch.object(stage.safe, "sha_file", side_effect=selective_sha), \
             mock.patch.object(stage.resume, "validate_completed",
                               side_effect=ValueError("RECORDED_MODEL_IDENTITY_MISMATCH")), \
             mock.patch.object(stage.resume, "run") as native, \
             mock.patch.object(stage.safe, "export", return_value={
                 "status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS", "errors": []
             }) as exported:
            report = stage.stage3(self.source, self.report, self.root / "work",
                                  installed=installed, execute=True,
                                  export_dest=self.root / "out")
        native.assert_not_called()
        exported.assert_called_once()
        self.assertFalse(report["native_execute_attempted"])
        self.assertEqual(report["status"], "STAGE3_RED_PRESERVED")
        self.assertIn("RECORDED_MODEL_IDENTITY_MISMATCH", str(report["errors"]))
        self.assertFalse(report["canonical_gate_pass"])

    def test_wrong_preflight_row_count_blocks_native_before_launch(self):
        installed = self.root / "installed"
        (installed / "bin").mkdir(parents=True)
        (installed / "bin/llama-server").write_bytes(b"synthetic only")
        original_sha = stage.safe.sha_file

        def selective_sha(path):
            if Path(path).name == "llama-server":
                return stage.RUN401_EXECUTABLE_SHA256
            return original_sha(path)

        with mock.patch.object(stage.safe, "sha_file", side_effect=selective_sha), \
             mock.patch.object(stage.resume, "validate_completed",
                               return_value={"rows": 41}), \
             mock.patch.object(stage.resume, "run") as native, \
             mock.patch.object(stage.safe, "export", return_value={
                 "status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS", "errors": []
             }):
            report = stage.stage3(self.source, self.report, self.root / "work",
                                  installed=installed, execute=True,
                                  export_dest=self.root / "out")
        native.assert_not_called()
        self.assertEqual(report["status"], "STAGE3_RED_PRESERVED")
        self.assertIn("STAGE3_PREFLIGHT_RECEIPT_INVALID", str(report["errors"]))

    def test_synthetic_native_failure_preserves_red_and_attempts(self):
        installed = self.root / "installed"
        (installed / "bin").mkdir(parents=True)
        (installed / "bin/llama-server").write_bytes(b"fake")
        failed = {"status": "INCOMPLETE",
                  "completed": {"O_s20": {}, "P_s20": {}},
                  "failures_preserved": {"S_s20": [{"reason": "synthetic"}]},
                  "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}
        original_sha_file = stage.safe.sha_file
        def selective_sha(path):
            if Path(path).name == "llama-server":
                return stage.RUN401_EXECUTABLE_SHA256
            return original_sha_file(path)
        with mock.patch.object(stage.safe, "sha_file",
                               side_effect=selective_sha), \
             mock.patch.object(stage.resume, "run", return_value=failed), \
             mock.patch.object(stage.resume, "validate_completed",
                               return_value={"rows": 42}), \
             mock.patch.object(stage.safe, "export",
                               return_value={"status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS",
                                             "errors": []}) as exported:
            report = stage.stage3(self.source, self.report, self.root / "work",
                                  installed=installed, execute=True,
                                  export_dest=self.root / "out")
        self.assertEqual(report["status"], "STAGE3_RED_PRESERVED")
        self.assertIn("STAGE3_NEXT_ARM_NOT_COMPLETE", str(report["errors"]))
        self.assertEqual(exported.call_count, 1)
        self.assertFalse(report["canonical_gate_pass"])


if __name__ == "__main__":
    unittest.main()
