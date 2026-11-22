"""Run117DH adversarial replay of exact original Run117DG native artifact."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts import run117dh_independent_normalized_native_audit as audit

ORIGINAL_SHA = "97570b164e2f888f16e3e9209c5edb6eb2f16ff2de2c2d033324e1359d30a4f8"
SOURCE_HEAD = "34b281608b5ffd55b7e77cda0152860f7e2ab302"


class Run117DHOriginalNativeMutations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("V13_RUN117DG_ORIGINAL_ZIP")
        if not path or not Path(path).is_file():
            raise RuntimeError("RUN117DG_ORIGINAL_NATIVE_ZIP_REQUIRED_NOT_SYNTHETIC")
        cls.path = Path(path)
        with zipfile.ZipFile(cls.path) as z:
            cls.report = json.loads(z.read("NATIVE_CASE/report.json"))

    def changed(self, mutation):
        r = copy.deepcopy(self.report)
        mutation(r)
        return r

    def test_exact_original_zip_48_native_receipts_and_negative_result(self):
        r = audit.audit_zip(self.path, expected_sha256=ORIGINAL_SHA,
                            expected_head=SOURCE_HEAD)
        self.assertEqual(r["inner_sha256_verified"], 26)
        self.assertEqual(r["native_final"], 48)
        self.assertEqual(r["process_reaped"], 48)
        self.assertEqual(r["status"], "NO_EXPLORATORY_NORMALIZED_SOURCE_SIGNAL")
        s = r["summary"]
        self.assertEqual(s["strict_scores"]["qwen35_0p8b"],
                         {"RAW": 4, "NORMALIZED": 4})
        self.assertEqual(s["none_output_count"]["qwen35_0p8b"],
                         {"RAW": 12, "NORMALIZED": 0})
        self.assertEqual(s["paired"]["qwen35_0p8b"],
                         {"normalized_only": 4, "raw_only": 4})
        self.assertFalse(r["redmi_measured"])

    def test_wrong_source_labels_or_ref_shape_rejected(self):
        r = self.changed(lambda x: x["rows"][0].update(expected="B"))
        with self.assertRaisesRegex(audit.AuditError, "ROW_SOURCE_OR_ORDER_RED"):
            audit.audit_report(r)
        r = self.changed(lambda x: x["rows"][0].update(source_ref_sha256=["bad"]))
        with self.assertRaisesRegex(audit.AuditError, "SOURCE_REF_SHAPE_RED"):
            audit.audit_report(r)

    def test_wrong_model_source_runner_and_authority_gates_rejected(self):
        r = self.changed(lambda x: x["model_pins"][0].update(revision="unregistered"))
        with self.assertRaisesRegex(audit.AuditError, "MODEL_PIN_RED"):
            audit.audit_report(r)
        r = self.changed(lambda x: x["source_pins"].update(
            {"scripts/run117df_paired_source_preflight.py": "0" * 40}))
        with self.assertRaisesRegex(audit.AuditError, "SOURCE_PIN_RED"):
            audit.audit_report(r)
        r = self.changed(lambda x: x.update(runner_sha256="0" * 64))
        with self.assertRaisesRegex(audit.AuditError, "RUNNER_PIN_RED"):
            audit.audit_report(r)
        r = self.changed(lambda x: x.update(step2="UTILITY_PASS"))
        with self.assertRaisesRegex(audit.AuditError, "NEGATIVE_GATES_RED"):
            audit.audit_report(r)

    def test_missing_native_final_reap_or_48_receipts_rejected(self):
        r = self.changed(lambda x: x["rows"][0]["arms"][0].update(process_reaped=False))
        with self.assertRaisesRegex(audit.AuditError, "NATIVE_ARM_RECEIPT_RED"):
            audit.audit_report(r)
        r = self.changed(lambda x: x.update(native_calls_verified=47))
        with self.assertRaisesRegex(audit.AuditError, "NATIVE_RECEIPT_COUNT_RED"):
            audit.audit_report(r)
        r = self.changed(lambda x: x.update(native_proof=False))
        with self.assertRaisesRegex(audit.AuditError, "NATIVE_RECEIPT_COUNT_RED"):
            audit.audit_report(r)

    def test_raw_hash_strict_score_summary_and_false_signal_rejected(self):
        r = self.changed(lambda x: x["rows"][0]["arms"][0].update(native_output="tampered"))
        with self.assertRaisesRegex(audit.AuditError, "RAW_HASH_RED"):
            audit.audit_report(r)
        r = self.changed(lambda x: x["rows"][0]["arms"][0].update(exact=True))
        with self.assertRaisesRegex(audit.AuditError, "STRICT_SCORER_RED"):
            audit.audit_report(r)
        r = self.changed(lambda x: x["summary"]["strict_scores"]["lfm25_350m"].update(RAW=12))
        with self.assertRaisesRegex(audit.AuditError, "SUMMARY_RECOMPUTE_RED"):
            audit.audit_report(r)
        r = self.changed(lambda x: x.update(status="EXPLORATORY_NORMALIZED_SOURCE_SIGNAL_NONPROMOTING"))
        with self.assertRaisesRegex(audit.AuditError, "STATUS_OR_PROMOTION_RED"):
            audit.audit_report(r)

    def test_outer_archive_hash_and_inner_manifest_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp) / "repacked.zip"
            outer.write_bytes(self.path.read_bytes() + b"unregistered-edit")
            with self.assertRaisesRegex(audit.AuditError, "ORIGINAL_ARCHIVE_SHA_RED"):
                audit.audit_zip(outer, expected_sha256=ORIGINAL_SHA,
                                expected_head=SOURCE_HEAD)
            inner = Path(tmp) / "changed-inner.zip"
            with zipfile.ZipFile(self.path) as src, zipfile.ZipFile(inner, "w") as out:
                for name in src.namelist():
                    raw = src.read(name)
                    if name == "NATIVE_RAW.log":
                        raw += b"\nUNREGISTERED_EDIT\n"
                    out.writestr(name, raw)
            with self.assertRaisesRegex(audit.AuditError, "INNER_SHA_RED"):
                audit.audit_zip(inner, expected_sha256=hashlib.sha256(inner.read_bytes()).hexdigest(),
                                expected_head=SOURCE_HEAD)


if __name__ == "__main__":
    unittest.main()
