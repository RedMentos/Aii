"""Run413 source-only adversarial no-model export receipt tests."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import run413_export_receipt_gate as gate


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class Run413ExportReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "safe-export"
        self.root.mkdir()
        self.progress = {
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
            "completed": {"O_s20": {}, "P_s20": {}}, "failures_preserved": {}}
        files = {
            "RUN397_PROGRESS.json": json.dumps(self.progress).encode(),
            "RUN394_PREREGISTERED_FIXTURES.json": b"{}",
            "attempts/O_s20/attempt-0001/native.json": b'{"raw":true}',
        }
        copied = {}
        for name, raw in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            copied[name] = {"sha256": sha(raw), "bytes": len(raw)}
        self.manifest = {
            "schema": "RUN409_SAFE_NATIVE_EXPORT_V1",
            "source_run": "Run397", "copied": copied,
            "omitted_installed_symlinks": [
                "attempts/P_s20/attempt-0001/P_s20-home/models"],
            "directories": [".", "attempts", "attempts/O_s20",
                            "attempts/O_s20/attempt-0001"],
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
        self.reseal()

    def reseal(self):
        (self.root / gate.MANIFEST).write_text(json.dumps(self.manifest, sort_keys=True))
        self.report["safe_export"]["manifest_sha256"] = gate.sha_file(self.root / gate.MANIFEST)

    def test_good_synthetic_export_remains_nonpromoting(self):
        result = gate.verify(self.root, self.report)
        self.assertEqual(result["status"], "RUN413_EXPORT_VERIFIED_NATIVE_PARTIAL")
        self.assertFalse(result["canonical_gate_pass"])

    def test_preserved_native_red_is_not_misreported_as_success(self):
        self.report.update(status="STAGE2_RED_PRESERVED",
                           native_execution_performed=False)
        self.progress["completed"].pop("P_s20")
        (self.root / "RUN397_PROGRESS.json").write_text(json.dumps(self.progress))
        raw = (self.root / "RUN397_PROGRESS.json").read_bytes()
        self.manifest["copied"]["RUN397_PROGRESS.json"] = {
            "sha256": sha(raw), "bytes": len(raw)}
        self.report["safe_export"]["copied_bytes"] = sum(
            x["bytes"] for x in self.manifest["copied"].values())
        self.reseal()
        result = gate.verify(self.root, self.report)
        self.assertEqual(result["status"], "RUN413_EXPORT_VERIFIED_NATIVE_RED")

    def test_mutated_export_bytes_are_rejected(self):
        (self.root / "attempts/O_s20/attempt-0001/native.json").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "EXPORT_FILE_METADATA_INVALID|EXPORT_HASH"):
            gate.verify(self.root, self.report)

    def test_unlisted_file_is_rejected(self):
        (self.root / "extra.txt").write_text("surprise")
        with self.assertRaisesRegex(ValueError, "UNLISTED_EXPORT_FILE"):
            gate.verify(self.root, self.report)

    def test_symlink_directory_is_rejected(self):
        (self.root / "bad-link").symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "EXPORT_SYMLINK_DIRECTORY"):
            gate.verify(self.root, self.report)

    def test_model_file_is_rejected_even_when_manifest_hash_matches(self):
        path = self.root / "attempts/O_s20/model.gguf"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake")
        self.manifest["copied"]["attempts/O_s20/model.gguf"] = {
            "sha256": sha(b"fake"), "bytes": 4}
        self.report["safe_export"]["copied_files"] += 1
        self.report["safe_export"]["copied_bytes"] += 4
        self.reseal()
        with self.assertRaisesRegex(ValueError, "MODEL_PATH_IN_EXPORT"):
            gate.verify(self.root, self.report)

    def test_false_gate_and_native_84_row_claims_are_rejected(self):
        for field, value in (("canonical_gate_pass", True),
                             ("jepa_weight", 0.1),
                             ("redmi_measured", True),
                             ("rows_verified", 42),
                             ("completed", ["O_s20"])):
            with self.subTest(field=field):
                d = copy.deepcopy(self.report)
                d[field] = value
                with self.assertRaises(ValueError):
                    gate.verify(self.root, d)

    def test_progress_cannot_claim_promoted_step2(self):
        self.progress["canonical_gate_pass"] = True
        (self.root / "RUN397_PROGRESS.json").write_text(json.dumps(self.progress))
        raw = (self.root / "RUN397_PROGRESS.json").read_bytes()
        self.manifest["copied"]["RUN397_PROGRESS.json"] = {
            "sha256": sha(raw), "bytes": len(raw)}
        self.report["safe_export"]["copied_bytes"] = sum(
            x["bytes"] for x in self.manifest["copied"].values())
        self.reseal()
        with self.assertRaisesRegex(ValueError, "PROGRESS_FALSE_PROMOTION"):
            gate.verify(self.root, self.report)

    def test_manifest_tamper_and_bad_omission_fail(self):
        d = copy.deepcopy(self.report)
        d["safe_export"]["manifest_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "EXPORT_MANIFEST_SHA_MISMATCH"):
            gate.verify(self.root, d)
        self.manifest["omitted_installed_symlinks"] = ["../models"]
        self.reseal()
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_OMITTED_SYMLINK"):
            gate.verify(self.root, self.report)


if __name__ == "__main__":
    unittest.main()
