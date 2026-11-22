"""Run117AN independent original ZIP audit and adversarial mutation tests."""
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import unittest
import zipfile

from scripts.run117an_independent_original_artifact_audit import (
    PINS, audit_bytes,
)


def repack(original, edits=None, *, regenerate_manifest=True, duplicate=None):
    edits = edits or {}
    with zipfile.ZipFile(BytesIO(original)) as z:
        files = {name: z.read(name) for name in z.namelist()}
    files.update(edits)
    if regenerate_manifest:
        files["SHA256SUMS"] = "".join(
            sha256(value).hexdigest() + "  ./" + name + "\n"
            for name, value in sorted(files.items()) if name != "SHA256SUMS"
        ).encode()
    out = BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
        if duplicate:
            z.writestr(duplicate, files[duplicate])
    return out.getvalue()


class OriginalArtifactAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blobs = {}
        for label in PINS:
            path = os.environ.get("RUN117AN_" + label)
            if not path or not Path(path).is_file():
                raise RuntimeError("RUN117AN_ORIGINAL_ZIP_MISSING_" + label)
            cls.blobs[label] = Path(path).read_bytes()

    def check_tamper(self, label, blob, reason):
        with self.assertRaisesRegex(ValueError, "RUN117AN_" + reason + "_RED"):
            audit_bytes(blob, label, expected_outer=sha256(blob).hexdigest())

    def test_three_originals_exact_and_negative_gates(self):
        for label in PINS:
            with self.subTest(label=label):
                result = audit_bytes(self.blobs[label], label)
                self.assertEqual(result["status"], PINS[label]["status"])
                self.assertFalse(result["native_inference_by_auditor"])
                self.assertFalse(result["whole_system_complete"])
                self.assertEqual(result["jepa_weight"], 0)

    def test_wrong_outer_digest_rejected_before_zip(self):
        for label in PINS:
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, "RUN117AN_OUTER_SHA_RED"):
                    audit_bytes(self.blobs[label] + b"x", label)

    def test_modified_raw_without_manifest_rejected(self):
        original = self.blobs["AJ"]
        with zipfile.ZipFile(BytesIO(original)) as z:
            raw = z.read("FULL_RAW.log")
        tampered = repack(original, {"FULL_RAW.log": raw + b"forged\n"},
                          regenerate_manifest=False)
        self.check_tamper("AJ", tampered, "INNER_SHA")

    def test_forged_original_fullsuite_green_rejected(self):
        original = self.blobs["AJ"]
        with zipfile.ZipFile(BytesIO(original)) as z:
            result = json.loads(z.read("RESULT.json"))
        result["exits"]["FULL"] = 0
        raw = (json.dumps(result, sort_keys=True) + "\n").encode()
        tampered = repack(original, {"RESULT.json": raw, "RESULT_RAW.log": raw,
                                     "FULL_EXIT.txt": b"0\n"})
        self.check_tamper("AJ", tampered, "EXIT_FORGED")

    def test_removed_original_failure_summary_rejected(self):
        original = self.blobs["AJ"]
        with zipfile.ZipFile(BytesIO(original)) as z:
            log = z.read("FULL_RAW.log")
        needle = b"FAILED (failures=5, errors=68, skipped=28)"
        self.assertIn(needle, log)
        tampered = repack(original, {"FULL_RAW.log": log.replace(needle, b"OK")})
        self.check_tamper("AJ", tampered, "ORIGINAL_FULLSUITE_RED")

    def test_changed_source_head_rejected(self):
        tampered = repack(self.blobs["AL"], {"HEAD.txt": b"forged\n"})
        self.check_tamper("AL", tampered, "SOURCE_HEAD")

    def test_unsafe_negative_gate_rejected(self):
        original = self.blobs["AM"]
        with zipfile.ZipFile(BytesIO(original)) as z:
            result = json.loads(z.read("RESULT.json"))
        result["jepa_weight"] = 1
        raw = (json.dumps(result, sort_keys=True) + "\n").encode()
        tampered = repack(original, {"RESULT.json": raw, "RESULT_RAW.log": raw})
        self.check_tamper("AM", tampered, "NEGATIVE_GATES")

    def test_duplicate_zip_entry_rejected(self):
        original = self.blobs["AL"]
        tampered = repack(original, duplicate="HEAD.txt")
        self.check_tamper("AL", tampered, "ZIP_MEMBERS")

    def test_extra_unmanifested_member_rejected(self):
        tampered = repack(self.blobs["AM"], {"unexpected.txt": b"x"},
                          regenerate_manifest=False)
        self.check_tamper("AM", tampered, "ZIP_MEMBERS")


if __name__ == "__main__":
    unittest.main()
