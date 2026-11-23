"""Adversarial software tests for immutable Run117DA original artifact audit."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts import run117dd_independent_native_audit as audit


class Run117DDOriginalAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original = os.environ.get("V13_RUN117DA_ORIGINAL_ZIP")
        if not original or not Path(original).is_file():
            raise RuntimeError("ORIGINAL_RUN117DA_ARTIFACT_REQUIRED_NOT_SYNTHETIC")
        cls.original = Path(original)
        with zipfile.ZipFile(cls.original) as z:
            cls.report = json.loads(z.read("NATIVE_CASE/report.json"))

    def changed(self, change):
        row = copy.deepcopy(self.report)
        change(row)
        return row

    def test_original_zip_crc_25_inner_sha_and_48_receipts(self):
        result = audit.audit_zip(self.original)
        self.assertEqual(result["inner_sha256_verified"], 25)
        self.assertEqual(result["native_calls"], 48)
        self.assertEqual(result["result"], "NO_EXPLORATORY_SCHEMA_SIGNAL")
        self.assertFalse(result["redmi_measured"])

    def test_oracle_and_source_label_tamper(self):
        r = self.changed(lambda x: x["rows"][0].update(expected="B"))
        with self.assertRaisesRegex(audit.AuditError, "ROW_SOURCE_OR_ORDER_RED"):
            audit.audit_report(r)
        r = self.changed(lambda x: x["rows"][0]["source_sha256"].update(current="0" * 64))
        with self.assertRaisesRegex(audit.AuditError, "ROW_SOURCE_OR_ORDER_RED"):
            audit.audit_report(r)

    def test_missing_row_or_reordered_arms(self):
        r = self.changed(lambda x: x["rows"].pop())
        with self.assertRaisesRegex(audit.AuditError, "ROW_COUNT_RED"):
            audit.audit_report(r)
        r = self.changed(lambda x: x["rows"][0]["arms"].reverse())
        with self.assertRaisesRegex(audit.AuditError, "ARM_ORDER_RED"):
            audit.audit_report(r)

    def test_wrong_model_and_source_pins(self):
        r = self.changed(lambda x: x["model_pins"][0].update(sha256="0" * 64))
        with self.assertRaisesRegex(audit.AuditError, "MODEL_PIN_RED"):
            audit.audit_report(r)
        r = self.changed(lambda x: x["source_pins"].update(
            {"scripts/run117da_disjoint_schema_fixture.py": "0" * 40}))
        with self.assertRaisesRegex(audit.AuditError, "SOURCE_PIN_RED"):
            audit.audit_report(r)

    def test_partial_native_or_missing_reap_cannot_pass(self):
        r = self.changed(lambda x: x["rows"][0]["arms"][0].update(process_reaped=False))
        with self.assertRaisesRegex(audit.AuditError, "NATIVE_ARM_RECEIPT_RED"):
            audit.audit_report(r)
        r = self.changed(lambda x: x.update(native_calls_verified=47))
        with self.assertRaisesRegex(audit.AuditError, "NATIVE_RECEIPT_COUNT_RED"):
            audit.audit_report(r)

    def test_raw_output_hash_and_summary_tamper(self):
        r = self.changed(lambda x: x["rows"][0]["arms"][0].update(native_output="different"))
        with self.assertRaisesRegex(audit.AuditError, "RAW_HASH_RED"):
            audit.audit_report(r)
        r = self.changed(lambda x: x["summary"]["strict_scores"]["lfm25_350m"].update(SCHEMA=12))
        with self.assertRaisesRegex(audit.AuditError, "SUMMARY_RECOMPUTE_RED"):
            audit.audit_report(r)

    def test_nonpromotion_and_authority_cannot_change(self):
        r = self.changed(lambda x: x.update(step2="PASS"))
        with self.assertRaisesRegex(audit.AuditError, "NEGATIVE_GATES_RED"):
            audit.audit_report(r)
        r = self.changed(lambda x: x.update(status="UTILITY_PASS"))
        with self.assertRaisesRegex(audit.AuditError, "NON_PROMOTION_RED"):
            audit.audit_report(r)

    def test_strict_parser_never_awards_markdown_or_extra_fields(self):
        for raw in ('```json\n{"action":"A"}\n```',
                    '{"action":"A","action":"B"}',
                    '{"action":"A","extra":1}',
                    '{"action":NaN}', 'A', ' {"action":"A"} garbage'):
            with self.subTest(raw=raw):
                self.assertIsNone(audit.decode(raw))
        self.assertEqual(audit.decode('{"action":"A"}'), "A")

    def test_outer_archive_hash_detects_repacking(self):
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "copy.zip"
            other.write_bytes(self.original.read_bytes() + b"modified")
            with self.assertRaisesRegex(audit.AuditError, "ORIGINAL_ARCHIVE_SHA_RED"):
                audit.audit_zip(other)

    def test_inner_sha_detects_changed_log_without_rewriting_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "changed.zip"
            with zipfile.ZipFile(self.original) as z, zipfile.ZipFile(other, "w") as out:
                for name in z.namelist():
                    content = z.read(name)
                    if name == "NATIVE_RAW.log":
                        content += b"\nUNREGISTERED_EDIT\n"
                    out.writestr(name, content)
            with self.assertRaisesRegex(audit.AuditError, "INNER_SHA_RED"):
                audit.audit_zip(other, expected_sha=None)


if __name__ == "__main__":
    unittest.main()
