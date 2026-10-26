"""Run440 RED-first: mixed-case model directories must not enter no-model exports.

Synthetic software-only fixtures; no model weights or native inference.
"""
import tempfile
import unittest
from pathlib import Path

from scripts import run409_safe_export as export
from scripts import run413_export_receipt_gate as receipt


class Run440CasefoldModelPath(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / "work"
        self.work.mkdir()
        self.installed = self.root / "installed"
        self.installed.mkdir()
        (self.work / "RUN397_PROGRESS.json").write_text('{"canonical_gate_pass":false}')
        self.dest = self.root / "no-model-export"

    def test_mixed_case_model_directory_with_opaque_payload_is_rejected(self):
        target = self.work / "attempts/O_s20/attempt-0001/arm_home/MoDeLs"
        target.mkdir(parents=True)
        (target / "renamed.data").write_bytes(b"synthetic-opaque-model-shaped-payload")
        result = export.export(self.work, self.installed, self.dest)
        self.assertEqual(result["status"], "EXPORT_RED_PRESERVED", result)
        self.assertIn("MODEL_OR_MANIFEST_FILE_IN_WORK", str(result["errors"]))
        self.assertFalse(self.dest.exists())

    def test_empty_mixed_case_model_directory_is_not_exported(self):
        (self.work / "MoDeLs").mkdir()
        result = export.export(self.work, self.installed, self.dest)
        self.assertEqual(result["status"], "EXPORT_RED_PRESERVED", result)
        self.assertIn("MODEL", str(result["errors"]))
        self.assertFalse(self.dest.exists())

    def test_independent_receipt_path_guard_rejects_case_variants(self):
        for part in ("Models", "MODELS", "MoDeLs"):
            with self.subTest(part=part):
                with self.assertRaisesRegex(ValueError, "MODEL_PATH_IN_EXPORT"):
                    receipt.safe_rel(f"attempts/O_s20/attempt-0001/arm_home/{part}/renamed.data")

    def test_normal_non_model_directory_stays_allowed(self):
        (self.work / "metadata").mkdir()
        (self.work / "metadata" / "report.data").write_bytes(b"synthetic")
        result = export.export(self.work, self.installed, self.dest)
        self.assertEqual(result["status"], "EXPORT_VERIFIED_NO_MODEL_WEIGHTS", result)
        self.assertTrue((self.dest / "metadata/report.data").is_file())
        self.assertEqual(receipt.safe_rel("metadata/report.data"), "metadata/report.data")


if __name__ == "__main__":
    unittest.main()
