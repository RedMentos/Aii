"""Run419 independent stage3 export/126-row gate, synthetic and fail-closed."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run419_verify_stage3_native as audit
import run413_export_receipt_gate as gate


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class Run419Native126Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "export"
        self.root.mkdir()
        self.receipt = {"rows": 42, "sha256": {"source": "synthetic"}}
        completed = {rid: {"attempt": "attempts/" + rid + "/attempt-0001",
                           "validated": self.receipt}
                     for rid in audit.PREFIX}
        progress = {"canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
                    "completed": completed, "failures_preserved": {}}
        frozen = audit.r394.manifest(audit.r394.FIXTURES, False,
                                     list(audit.r394.ARMS),
                                     list(audit.r394.SEEDS))
        files = {"RUN397_PROGRESS.json": json.dumps(progress).encode(),
                 "RUN394_PREREGISTERED_FIXTURES.json": json.dumps(frozen).encode()}
        for rid in audit.PREFIX:
            files["attempts/" + rid + "/attempt-0001/native.json"] = b'{"synthetic":true}'
        self.manifest = {"schema": "RUN409_SAFE_NATIVE_EXPORT_V1",
                         "source_run": "Run397",
                         "copied": {}, "omitted_installed_symlinks": [],
                         "directories": [".", "attempts"],
                         "canonical_gate_pass": False,
                         "step2_exit": "UTILITY_FAIL"}
        for rid in audit.PREFIX:
            self.manifest["directories"] += ["attempts/" + rid,
                "attempts/" + rid + "/attempt-0001"]
        for name, raw in files.items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
            self.manifest["copied"][name] = {"sha256": sha(raw), "bytes": len(raw)}
        self.report = {"run": "Run415",
                       "status": "STAGE3_NATIVE_PARTIAL_NO_PROMOTION",
                       "errors": [], "native_execute_requested": True,
                       "native_execute_attempted": True,
                       "native_execution_performed": True,
                       "rows_verified": 126, "completed": list(audit.PREFIX),
                       "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
                       "redmi_measured": False, "jepa_weight": 0,
                       "progress_sha256": audit.sha_file(self.root / "RUN397_PROGRESS.json"),
                       "safe_export": {"status": "EXPORT_VERIFIED_NO_MODEL_WEIGHTS",
                                       "errors": [],
                                       "copied_files": len(files),
                                       "copied_bytes": sum(len(x) for x in files.values())}}
        self.seal()

    def seal(self):
        p = self.root / gate.MANIFEST
        p.write_text(json.dumps(self.manifest, sort_keys=True))
        self.report["safe_export"]["manifest_sha256"] = audit.sha_file(p)

    def verify(self):
        with mock.patch.object(audit.resume, "validate_completed",
                               return_value=self.receipt) as checked:
            result = audit.verify(self.root, self.report)
        return result, checked

    def test_all_three_receipts_checked_before_green(self):
        result, checked = self.verify()
        self.assertEqual(result["status"], "RUN419_NATIVE_126_INDEPENDENTLY_VERIFIED")
        self.assertEqual(result["rows_verified"], 126)
        self.assertEqual(checked.call_count, 3)
        self.assertEqual({c.args[1] for c in checked.call_args_list}, {"O", "P", "S"})
        self.assertTrue(all(c.kwargs["current_runner_sha"] ==
                            audit.RUN401_EXECUTABLE_SHA256
                            for c in checked.call_args_list))
        self.assertFalse(result["canonical_gate_pass"])

    def test_wrong_native_row_count_cannot_pass(self):
        with mock.patch.object(audit.resume, "validate_completed",
                               return_value={"rows": 41}):
            with self.assertRaisesRegex(ValueError, "STAGE3_NATIVE_RECEIPT_INVALID"):
                audit.verify(self.root, self.report)

    def test_false_native_status_or_gate_rejected(self):
        for key, value in (("status", "STAGE3_RED_PRESERVED"),
                           ("rows_verified", 84),
                           ("jepa_weight", 0.1),
                           ("redmi_measured", True),
                           ("canonical_gate_pass", True)):
            with self.subTest(key=key):
                old = self.report[key]
                self.report[key] = value
                with self.assertRaisesRegex(ValueError, "STAGE3_NATIVE_126_NOT_GREEN"):
                    audit.verify(self.root, self.report)
                self.report[key] = old

    def test_tampered_native_file_rejected_before_receipt_validation(self):
        p = self.root / "attempts/S_s20/attempt-0001/native.json"
        p.write_bytes(b"tampered")
        with mock.patch.object(audit.resume, "validate_completed") as checked:
            with self.assertRaisesRegex(ValueError, "EXPORT_FILE_METADATA_INVALID|EXPORT_HASH"):
                audit.verify(self.root, self.report)
            checked.assert_not_called()

    def test_missing_or_extra_file_rejected(self):
        (self.root / "extra.txt").write_text("unlisted")
        with self.assertRaisesRegex(ValueError, "UNLISTED_EXPORT_FILE"):
            audit.verify(self.root, self.report)

    def test_attempt_traversal_even_with_resealed_progress_rejected(self):
        p = self.root / "RUN397_PROGRESS.json"
        progress = json.loads(p.read_text())
        progress["completed"]["O_s20"]["attempt"] = "../outside"
        p.write_text(json.dumps(progress))
        raw = p.read_bytes()
        self.manifest["copied"][p.name] = {"sha256": sha(raw), "bytes": len(raw)}
        self.report["safe_export"]["copied_bytes"] = sum(
            v["bytes"] for v in self.manifest["copied"].values())
        self.report["progress_sha256"] = sha(raw)
        self.seal()
        with self.assertRaisesRegex(ValueError, "STAGE3_ATTEMPT_PATH_INVALID"):
            audit.verify(self.root, self.report)

    def test_missing_native_receipt_is_red_not_promoted(self):
        with mock.patch.object(audit.resume, "validate_completed",
                               side_effect=ValueError("NATIVE_RECEIPT_MISSING")):
            with self.assertRaisesRegex(ValueError, "NATIVE_RECEIPT_MISSING"):
                audit.verify(self.root, self.report)


if __name__ == "__main__":
    unittest.main()
