"""Run418 source-only ZIP import tests; no models, no native execution."""
import hashlib
import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

import run418_import_no_model_artifact as importer
import run413_export_receipt_gate as gate


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class Run418ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        progress = {"canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
                    "completed": {"O_s20": {}, "P_s20": {}},
                    "failures_preserved": {}}
        files = {"RUN397_PROGRESS.json": json.dumps(progress).encode(),
                 "RUN394_PREREGISTERED_FIXTURES.json": b"{}",
                 "attempts/O_s20/attempt-0001/native.json": b'{"raw":true}'}
        copied = {}
        for name, raw in files.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            copied[name] = {"sha256": sha(raw), "bytes": len(raw)}
        empty = self.source / "attempts/P_s20/attempt-0001/empty"
        empty.mkdir(parents=True)
        self.manifest = {
            "schema": "RUN409_SAFE_NATIVE_EXPORT_V1", "source_run": "Run397",
            "copied": copied, "omitted_installed_symlinks": [],
            "directories": [".", "attempts", "attempts/O_s20",
                            "attempts/O_s20/attempt-0001", "attempts/P_s20",
                            "attempts/P_s20/attempt-0001",
                            "attempts/P_s20/attempt-0001/empty"],
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}
        self.report = {
            "run": "Run411", "status": "STAGE2_NATIVE_PARTIAL_NO_PROMOTION",
            "native_execute_requested": True, "native_execute_attempted": True,
            "native_execution_performed": True, "rows_verified": 84,
            "completed": ["O_s20", "P_s20"],
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
            "redmi_measured": False, "jepa_weight": 0,
            "safe_export": {"status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS",
                            "errors": [], "copied_files": len(copied),
                            "copied_bytes": sum(x["bytes"] for x in copied.values())}}
        self.seal()
        self.archive = self.root / "artifact.zip"
        self.write_zip()

    def seal(self):
        path = self.source / gate.MANIFEST
        path.write_text(json.dumps(self.manifest, sort_keys=True))
        self.report["safe_export"]["manifest_sha256"] = sha(path.read_bytes())

    def write_zip(self, extra=None, omit=None):
        with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for path in sorted(self.source.rglob("*")):
                if path.is_file() and path.relative_to(self.source).as_posix() != omit:
                    z.write(path, path.relative_to(self.source).as_posix())
            if extra:
                for name, raw in extra:
                    z.writestr(name, raw)
        self.digest = importer.sha_file(self.archive)

    def run_import(self, digest=None):
        return importer.import_artifact(self.archive, digest or self.digest,
                                        self.report, self.root / "restored")

    def test_realistic_actions_zip_omits_empty_directory_and_is_restored(self):
        result = self.run_import()
        self.assertEqual(result["status"], "RUN418_NO_MODEL_IMPORT_VERIFIED")
        self.assertEqual(result["restored_empty_directories"], 1)
        self.assertTrue((self.root / "restored/attempts/P_s20/attempt-0001/empty").is_dir())
        self.assertEqual(gate.verify(self.root / "restored", self.report)
                         ["status"], "RUN413_EXPORT_VERIFIED_NATIVE_PARTIAL")
        self.assertFalse(result["canonical_gate_pass"])

    def test_wrong_outer_artifact_hash_rejected_before_extract(self):
        with self.assertRaisesRegex(ValueError, "ARTIFACT_SHA_MISMATCH"):
            self.run_import("a" * 64)
        self.assertFalse((self.root / "restored").exists())

    def test_unlisted_and_missing_members_rejected(self):
        for extra, omit in (([("extra.txt", b"surprise")], None),
                            (None, "RUN397_PROGRESS.json")):
            with self.subTest(extra=extra, omit=omit):
                self.write_zip(extra, omit)
                with self.assertRaisesRegex(ValueError, "ARTIFACT_FILE_INVENTORY_MISMATCH"):
                    self.run_import()
                self.assertFalse((self.root / "restored").exists())

    def test_traversal_member_rejected(self):
        self.write_zip(extra=[("../outside", b"bad")])
        with self.assertRaisesRegex(ValueError, "UNSAFE_EXPORT_PATH"):
            self.run_import()
        self.assertFalse((self.root / "outside").exists())

    def test_duplicate_member_rejected(self):
        self.write_zip(extra=[("RUN397_PROGRESS.json", b"forged")])
        with self.assertRaisesRegex(ValueError, "DUPLICATE_ARTIFACT_MEMBER"):
            self.run_import()

    def test_resealed_manifest_mismatch_rejected(self):
        self.manifest["directories"].append("unregistered")
        self.seal()
        self.write_zip()
        self.report["safe_export"]["manifest_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "ARTIFACT_MANIFEST_SHA_MISMATCH"):
            self.run_import()

    def test_zip_symlink_member_rejected(self):
        link = zipfile.ZipInfo("bad-link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.write_zip(extra=[(link, b"../target")])
        with self.assertRaisesRegex(ValueError, "ARTIFACT_SPECIAL_FILE"):
            self.run_import()

    def test_native_red_report_never_imports_as_green(self):
        self.report["status"] = "STAGE2_RED_PRESERVED"
        with self.assertRaisesRegex(ValueError, "RUN413_NATIVE_NOT_GREEN"):
            self.run_import()

    def test_destination_never_overwritten(self):
        (self.root / "restored").mkdir()
        with self.assertRaisesRegex(ValueError, "DESTINATION_NOT_FRESH_OR_UNSAFE"):
            self.run_import()


if __name__ == "__main__":
    unittest.main()
