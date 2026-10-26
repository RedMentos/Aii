"""Run466 atomic native336 import/adversarial tests; synthetic only."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import warnings
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run466_import_stage8_artifact as importer


def encoded(obj):
    return (json.dumps(obj, sort_keys=True) + "\n").encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Run466AtomicImport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "safe.zip"
        self.destination = self.root / "published"
        self.files = {
            "RUN397_PROGRESS.json": encoded({"completed": {}, "step2_exit": "UTILITY_FAIL"}),
            "attempts/S_s21/tool.json": encoded({"rows": 42}),
        }
        self.dirs = [".", "attempts", "attempts/S_s21"]
        self.make_archive()
        self.report = {
            "run": "Run462", "status": "STAGE8_NATIVE_PARTIAL_NO_PROMOTION",
            "rows_verified": 336, "canonical_gate_pass": False,
            "step2_exit": "UTILITY_FAIL",
            "safe_export": {"manifest_sha256": self.manifest_sha},
        }

    def make_archive(self, extra=None, tamper=None):
        copied = {name: {"sha256": sha(data), "bytes": len(data)}
                  for name, data in self.files.items()}
        manifest = encoded({"copied": copied, "directories": self.dirs})
        self.manifest_sha = sha(manifest)
        with zipfile.ZipFile(self.archive, "w") as z:
            for name, data in self.files.items():
                z.writestr(name, tamper if name == "attempts/S_s21/tool.json"
                           and tamper is not None else data)
            z.writestr(importer.gate.MANIFEST, manifest)
            for name, data in extra or []:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    z.writestr(name, data)
        self.outer_sha = importer.audit.sha_file(self.archive)

    def run_import(self, expected=None, report=None, verifier=None):
        def check(stage, r):
            self.assertFalse(self.destination.exists(),
                             "destination must not exist during validation")
            if verifier:
                return verifier(stage, r)
            return {"status": "RUN465_NATIVE_336_INDEPENDENTLY_VERIFIED",
                    "rows_verified": 336, "canonical_gate_pass": False,
                    "step2_exit": "UTILITY_FAIL",
                    "manifest_sha256": self.manifest_sha,
                    "copied_files": len(self.files),
                    "copied_bytes": sum(len(x) for x in self.files.values())}

        with patch.object(importer.audit, "verify", side_effect=check):
            return importer.import_stage8(
                self.archive, expected or self.outer_sha,
                report if report is not None else self.report, self.destination)

    def test_seven_receipts_verified_before_atomic_publication(self):
        result = self.run_import()
        self.assertTrue(self.destination.is_dir())
        self.assertFalse((self.destination / importer.gate.MANIFEST).exists(),
                         "prior export manifest must not enter reusable work")
        installed = self.root / "installed"
        installed.mkdir()
        exported = importer.safe.export(self.destination, installed,
                                        self.root / "next-safe-export")
        self.assertEqual(exported["status"], "EXPORT_VERIFIED_NO_MODEL_WEIGHTS",
                         exported["errors"])
        self.assertTrue((self.root / "next-safe-export" /
                         importer.gate.MANIFEST).is_file())
        self.assertEqual(result["rows_verified"], 336)
        self.assertEqual(result["step2_exit"], "UTILITY_FAIL")
        self.assertFalse(result["canonical_gate_pass"])
        self.assertEqual((self.destination / "RUN397_PROGRESS.json").read_bytes(),
                         self.files["RUN397_PROGRESS.json"])

    def test_wrong_outer_sha_refused_without_destination(self):
        with self.assertRaisesRegex(ValueError, "ARTIFACT_SHA_MISMATCH"):
            self.run_import(expected="0" * 64)
        self.assertFalse(self.destination.exists())

    def test_wrong_manifest_sha_refused_without_destination(self):
        self.report["safe_export"]["manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "ARTIFACT_MANIFEST_SHA_MISMATCH"):
            self.run_import()
        self.assertFalse(self.destination.exists())

    def test_false_positive_gate_refused_without_destination(self):
        self.report["canonical_gate_pass"] = True
        with self.assertRaisesRegex(ValueError, "NATIVE_336_NOT_GREEN"):
            self.run_import()
        self.assertFalse(self.destination.exists())

    def test_member_tamper_refused_without_destination(self):
        self.make_archive(tamper=encoded({"rows": 43}))
        with self.assertRaisesRegex(ValueError, "ARTIFACT_MEMBER_SHA_MISMATCH"):
            self.run_import()
        self.assertFalse(self.destination.exists())

    def test_duplicate_member_refused_without_destination(self):
        self.make_archive(extra=[("RUN397_PROGRESS.json", b"duplicate")])
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_MISSING"):
            self.run_import()
        self.assertFalse(self.destination.exists())

    def test_parent_escape_refused_without_destination(self):
        self.make_archive(extra=[("../outside", b"unsafe")])
        with self.assertRaisesRegex(ValueError, "UNSAFE_EXPORT_PATH"):
            self.run_import()
        self.assertFalse(self.destination.exists())

    def test_symlink_member_refused_without_destination(self):
        info = zipfile.ZipInfo("linked")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.make_archive(extra=[(info, b"../outside")])
        with self.assertRaisesRegex(ValueError, "ARTIFACT_SPECIAL_FILE"):
            self.run_import()
        self.assertFalse(self.destination.exists())

    def test_verifier_failure_refused_without_destination(self):
        def fail(stage, report):
            raise ValueError("SIX_RECEIPTS_RED")
        with self.assertRaisesRegex(ValueError, "SIX_RECEIPTS_RED"):
            self.run_import(verifier=fail)
        self.assertFalse(self.destination.exists())

    def test_forged_verifier_positive_gate_refused_without_destination(self):
        def forged(stage, report):
            return {"status": "RUN465_NATIVE_336_INDEPENDENTLY_VERIFIED",
                    "rows_verified": 336, "canonical_gate_pass": True,
                    "step2_exit": "UTILITY_FAIL"}
        with self.assertRaisesRegex(ValueError, "NATIVE_336_NOT_VERIFIED"):
            self.run_import(verifier=forged)
        self.assertFalse(self.destination.exists())

    def test_existing_destination_refused(self):
        self.destination.mkdir()
        with self.assertRaisesRegex(ValueError, "DESTINATION_NOT_FRESH"):
            self.run_import()


if __name__ == "__main__":
    unittest.main()
