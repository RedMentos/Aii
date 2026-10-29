"""Independent P0X original native evidence verifier regression tests."""
import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from scripts import p0x_native150_raw_independent_audit as audit


class Native150OriginalAudit(unittest.TestCase):
    def test_pinned_constants_and_no_gate(self):
        self.assertEqual(len(audit.HEAD), 40)
        self.assertEqual(len(audit.RAW_SHA), 64)
        self.assertEqual(len(audit.SCORE_SHA), 64)
        self.assertEqual(len(audit.STAGES), 13)

    def test_missing_root_rejected(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises((ValueError, FileNotFoundError)):
                audit.audit(Path(tmp))

    def test_zip_wrong_pin_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "wrong.zip"
            path.write_bytes(b"not the original archive")
            with self.assertRaisesRegex(ValueError, "ZIP_PIN"):
                audit.audit_zip(path)

    def test_unsafe_checksum_path_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "good.txt").write_text("ok")
            with self.assertRaisesRegex(ValueError, "UNSAFE_PATH"):
                audit.safe_file(root, "../escape")
            with self.assertRaisesRegex(ValueError, "UNSAFE_PATH"):
                audit.safe_file(root, "/tmp/escape")

    def test_original_150_rows_and_stage_tamper(self):
        env = os.environ.get("P0X_ORIGINAL_EVIDENCE")
        if not env:
            self.skipTest("original native artifact supplied only by review CI")
        root = Path(env)
        result = audit.audit(root)
        self.assertEqual(result["native_rows"], 150)
        self.assertEqual(result["model_output_labels"]["NONE"], 150)
        self.assertEqual(result["wrong_committed"], 100)
        self.assertFalse(result["canonical_gate_pass"])
        with TemporaryDirectory() as tmp:
            clone = Path(tmp) / "original"
            shutil.copytree(root, clone)
            (clone / "NATIVE_EXIT.txt").write_text("1\n")
            with self.assertRaisesRegex(ValueError, "CHECKSUM_MISMATCH|STAGE_NATIVE"):
                audit.audit(clone)


if __name__ == "__main__":
    unittest.main()
