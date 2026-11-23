"""Run117AP original 30-call native ZIP independent read-only adversarial tests."""
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import unittest
import warnings
import zipfile

from scripts.run117ap_independent_native_source_id_audit import (
    OUTER_SHA, audit_bytes,
)


def repack(original, edits=None, *, duplicate=None):
    edits = edits or {}
    with zipfile.ZipFile(BytesIO(original)) as z:
        files = {name: z.read(name) for name in z.namelist()}
    files.update(edits)
    files["SHA256SUMS"] = "".join(
        sha256(value).hexdigest() + "  ./" + name + "\n"
        for name, value in sorted(files.items()) if name != "SHA256SUMS"
    ).encode()
    out = BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                z.writestr(duplicate, files[duplicate])
    return out.getvalue()


def modify_report(original, mutate):
    with zipfile.ZipFile(BytesIO(original)) as z:
        report = json.loads(z.read("NATIVE_CASE/report.json"))
    mutate(report)
    return repack(original, {
        "NATIVE_CASE/report.json": (json.dumps(report, sort_keys=True) + "\n").encode()
    })


class NativeOriginalAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = os.environ.get("RUN117AP_ORIGINAL")
        if not p or not Path(p).is_file():
            raise RuntimeError("RUN117AP_ORIGINAL_NATIVE_ZIP_REQUIRED")
        cls.original = Path(p).read_bytes()

    def expect_red(self, data, code):
        with self.assertRaisesRegex(ValueError, "RUN117AP_" + code + "_RED"):
            audit_bytes(data, expected_outer=sha256(data).hexdigest())

    def test_original_exact_30_calls_and_independent_two_of_six(self):
        r = audit_bytes(self.original)
        self.assertEqual(sha256(self.original).hexdigest(), OUTER_SHA)
        self.assertEqual(r["status"], "INDEPENDENT_ORIGINAL_NATIVE_COMPLETE_LOW_UTILITY")
        self.assertEqual(r["native_body_calls"], 30)
        self.assertEqual(r["raw_packets_verified"], 48)
        self.assertEqual(r["body_id_correct_by_role"],
                         {"B1_DETAIL": 3, "B2_GIST": 4})
        self.assertEqual(r["body_id_pair_correct"], 2)
        self.assertEqual(r["baseline_quote_ready_reported"], 4)
        self.assertEqual(r["nested_source_files_verified"], 2304)
        self.assertFalse(r["model_weights_independently_rehashed"])
        self.assertFalse(r["whole_system_complete"])

    def test_outer_modified_rejected(self):
        with self.assertRaisesRegex(ValueError, "RUN117AP_OUTER_SHA_RED"):
            audit_bytes(self.original + b"forged")

    def test_changed_source_zip_rejected(self):
        with zipfile.ZipFile(BytesIO(self.original)) as z:
            source = z.read("V13-Phone-Run117AM.zip")
        self.expect_red(repack(self.original, {
            "V13-Phone-Run117AM.zip": source + b"forged"}), "SOURCE_ZIP_SHA")

    def test_forged_correctness_rejected(self):
        def mutate(r):
            r["rows"][0]["id_selections"][0]["model_id_correct"] = False
        self.expect_red(modify_report(self.original, mutate), "ID_SCORE_FORGED")

    def test_changed_authoritative_source_text_rejected(self):
        def mutate(r):
            r["rows"][0]["prior_source_text"] += " forged"
        self.expect_red(modify_report(self.original, mutate), "ROW_SOURCE")

    def test_missing_native_offer_rejected(self):
        def mutate(r):
            r["rows"][0]["offers"].pop()
        self.expect_red(modify_report(self.original, mutate), "ROW_SOURCE")

    def test_nonreaped_native_child_rejected(self):
        def mutate(r):
            r["rows"][0]["id_selections"][0]["process_reaped"] = False
        self.expect_red(modify_report(self.original, mutate), "ID_NATIVE")

    def test_forged_learning_authority_rejected(self):
        def mutate(r):
            r["jepa_weight"] = 1
        self.expect_red(modify_report(self.original, mutate), "NATIVE_REPORT_GATES")

    def test_modified_packet_raw_without_sha_rejected(self):
        def mutate(r):
            r["rows"][0]["id_selections"][0]["packet_evidence"]["raw"] += " "
        self.expect_red(modify_report(self.original, mutate), "RAW_PACKET_SHA")

    def test_changed_model_receipt_rejected(self):
        with zipfile.ZipFile(BytesIO(self.original)) as z:
            log = z.read("INSTALL_BODIES_RAW.log")
        old = b"bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1"
        self.assertIn(old, log)
        self.expect_red(repack(self.original, {
            "INSTALL_BODIES_RAW.log": log.replace(old, b"0" * 64)}), "MODEL_RECEIPT")

    def test_duplicate_outer_member_rejected(self):
        self.expect_red(repack(self.original, duplicate="HEAD.txt"), "ZIP_MEMBERS")


if __name__ == "__main__":
    unittest.main()
