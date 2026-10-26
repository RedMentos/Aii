"""Run438 synthetic native210 ZIP importer tests; mocked verifier is NOT native evidence."""
import copy
import stat
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import run438_import_stage5_artifact as importer
import run436_verify_native210 as audit
from tests.test_run419_verify_stage3_native import Run419Native126Tests


class Run438Stage5ImportTests(unittest.TestCase):
    def setUp(self):
        self.fixture = Run419Native126Tests("test_all_three_receipts_checked_before_green")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root.parent
        self.source = self.fixture.root
        self.archive = self.root / "stage5-synthetic.zip"
        self.report = copy.deepcopy(self.fixture.report)
        self.report.update(run="Run434", status="STAGE5_NATIVE_PARTIAL_NO_PROMOTION",
                           rows_verified=210)
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
        synthetic = {"status": "RUN436_NATIVE_210_INDEPENDENTLY_VERIFIED",
                     "manifest_sha256": self.report["safe_export"]["manifest_sha256"],
                     "copied_files": 50, "copied_bytes": 200}
        with mock.patch.object(importer.audit, "verify", return_value=synthetic) as checked:
            result = importer.import_stage5(
                self.archive, digest or self.digest, self.report,
                self.root / "restored")
        return result, checked

    def test_atomic_restore_only_after_mocked_independent_verifier(self):
        result, checked = self.run_import()
        self.assertEqual(result["status"], "RUN438_STAGE5_ARTIFACT_IMPORTED_VERIFIED")
        self.assertEqual(result["rows_verified"], 210)
        checked.assert_called_once()
        self.assertTrue((self.root / "restored/attempts/S_s20/attempt-0001").is_dir())
        self.assertFalse((self.root / "restored" / importer.gate.MANIFEST).exists(),
                         "imported export manifest must not enter reusable work")
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

    def test_false_210_native_report_rejected_before_import(self):
        for field, value in (("status", "STAGE5_RED_PRESERVED"),
                             ("rows_verified", 168)):
            with self.subTest(field=field):
                self.report[field] = value
                with self.assertRaisesRegex(ValueError, "NATIVE_210_NOT_GREEN"):
                    self.run_import()
                self.assertFalse((self.root / "restored").exists())
                self.report.update(status="STAGE5_NATIVE_PARTIAL_NO_PROMOTION",
                                   rows_verified=210)

    def test_independent_verifier_red_never_publishes(self):
        with mock.patch.object(importer.audit, "verify",
                               side_effect=ValueError("RECORDED_MODEL_IDENTITY_MISMATCH")):
            with self.assertRaisesRegex(ValueError, "RECORDED_MODEL_IDENTITY_MISMATCH"):
                importer.import_stage5(self.archive, self.digest, self.report,
                                       self.root / "restored")
        self.assertFalse((self.root / "restored").exists())


    def test_real_cli_stage5_report_and_atomic_publication(self):
        # Catch CLI/report naming mismatches before expensive native postflight.
        import json
        report_path = self.root / "stage5-report.json"
        report_path.write_text(json.dumps(self.report))
        output = self.root / "import-cli-result.json"
        argv = ["run438_import_stage5_artifact.py", "--archive", str(self.archive),
                "--expected-sha256", self.digest,
                "--stage5-report", str(report_path),
                "--destination", str(self.root / "restored"),
                "--output", str(output)]
        synthetic = {"status": "RUN436_NATIVE_210_INDEPENDENTLY_VERIFIED",
                     "manifest_sha256": self.report["safe_export"]["manifest_sha256"],
                     "copied_files": 50, "copied_bytes": 200}
        with mock.patch("sys.argv", argv), \
             mock.patch.object(importer.audit, "verify", return_value=synthetic):
            with self.assertRaises(SystemExit) as done:
                importer.main()
        self.assertEqual(done.exception.code, 0)
        self.assertEqual(json.loads(output.read_text())["status"],
                         "RUN438_STAGE5_ARTIFACT_IMPORTED_VERIFIED")


if __name__ == "__main__":
    unittest.main()
