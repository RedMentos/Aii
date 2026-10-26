"""Run419 Actions ZIP stage3 import; no native inference or model weights."""
import stat
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import run419_import_stage3_artifact as importer
import run419_verify_stage3_native as audit
from tests.test_run419_verify_stage3_native import Run419Native126Tests


class Run419Stage3ImportTests(unittest.TestCase):
    def setUp(self):
        self.fixture = Run419Native126Tests("test_all_three_receipts_checked_before_green")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root.parent
        self.source = self.fixture.root
        self.archive = self.root / "stage3.zip"
        self.write_zip()

    def write_zip(self, extra=None, omit=None):
        with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for p in sorted(self.source.rglob("*")):
                if p.is_file() and p.relative_to(self.source).as_posix() != omit:
                    z.write(p, p.relative_to(self.source).as_posix())
            if extra:
                for name, raw in extra:
                    z.writestr(name, raw)
        self.digest = audit.sha_file(self.archive)

    def run_import(self, digest=None):
        with mock.patch.object(audit.resume, "validate_completed",
                               return_value=self.fixture.receipt) as checked:
            result = importer.import_stage3(
                self.archive, digest or self.digest,
                self.fixture.report, self.root / "restored")
        return result, checked

    def test_restores_omitted_directories_and_checks_three_native_receipts(self):
        result, checked = self.run_import()
        self.assertEqual(result["status"], "RUN419_STAGE3_ARTIFACT_IMPORTED_VERIFIED")
        self.assertEqual(result["rows_verified"], 126)
        self.assertEqual(checked.call_count, 3)
        self.assertTrue((self.root / "restored/attempts/S_s20/attempt-0001").is_dir())
        self.assertFalse(result["canonical_gate_pass"])

    def test_wrong_outer_sha_rejected(self):
        with self.assertRaisesRegex(ValueError, "ARTIFACT_SHA_MISMATCH"):
            self.run_import("a" * 64)
        self.assertFalse((self.root / "restored").exists())

    def test_extra_and_missing_members_rejected(self):
        for extra, omit in (([("extra.txt", b"bad")], None),
                            (None, "RUN397_PROGRESS.json")):
            with self.subTest(extra=extra, omit=omit):
                self.write_zip(extra, omit)
                with self.assertRaisesRegex(ValueError, "ARTIFACT_INVENTORY_MISMATCH"):
                    self.run_import()
                self.assertFalse((self.root / "restored").exists())

    def test_traversal_and_symlink_rejected(self):
        self.write_zip(extra=[("../outside", b"bad")])
        with self.assertRaisesRegex(ValueError, "UNSAFE_EXPORT_PATH"):
            self.run_import()
        self.assertFalse((self.root / "outside").exists())
        link = zipfile.ZipInfo("bad-link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.write_zip(extra=[(link, b"../outside")])
        with self.assertRaisesRegex(ValueError, "ARTIFACT_SPECIAL_FILE"):
            self.run_import()

    def test_false_126_native_report_rejected_before_import(self):
        self.fixture.report["status"] = "STAGE3_RED_PRESERVED"
        with self.assertRaisesRegex(ValueError, "NATIVE_126_NOT_GREEN"):
            self.run_import()

    def test_tampered_native_receipt_rejected_by_independent_gate(self):
        with mock.patch.object(audit.resume, "validate_completed",
                               side_effect=ValueError("RECORDED_MODEL_IDENTITY_MISMATCH")):
            with self.assertRaisesRegex(ValueError, "RECORDED_MODEL_IDENTITY_MISMATCH"):
                importer.import_stage3(self.archive, self.digest,
                                       self.fixture.report, self.root / "restored")
        self.assertFalse((self.root / "restored").exists())


if __name__ == "__main__":
    unittest.main()
