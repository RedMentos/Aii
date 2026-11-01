"""Run117DH independent frozen cohort/scorer tests; no native model."""
import hashlib
import json
import tempfile
from pathlib import Path
import unittest

from scripts import run117dh_independent_normalized_native_audit as audit
from scripts import run117de_normalized_source_fixture as frozen


class Run117DHReadOnlyAudit(unittest.TestCase):
    def test_preregistered_table_hash_and_independent_oracle(self):
        self.assertEqual(audit.sha(json.dumps(audit.TABLE, sort_keys=True,
                                              separators=(",", ":")).encode()),
                         audit.TABLE_SHA256)
        self.assertEqual([audit._oracle(row) for row in audit.TABLE],
                         ["A", "B", "NONE"] * 4)
        self.assertEqual(audit.TABLE_SHA256, frozen.TABLE_SHA256)

    def test_independent_source_hashes_match_frozen_real_store_renderer(self):
        for row, f in zip(audit.TABLE, frozen.fixtures()):
            with self.subTest(project=row[0]):
                self.assertEqual(audit._sources(row), f["source_sha256"])

    def test_strict_parser_rejects_markdown_duplicates_extra_and_nonfinite(self):
        for raw in ('```json\n{"action":"A"}\n```',
                    '{"action":"A","action":"B"}',
                    '{"action":"A","extra":true}',
                    '{"action":NaN}', 'A', '{"action":null}',
                    '{"action":"C"}'):
            with self.subTest(raw=raw):
                self.assertIsNone(audit.decode(raw))
        self.assertEqual(audit.decode('{"action":"A"}'), "A")
        self.assertEqual(audit.decode('{"action":"NONE"}'), "NONE")

    def test_missing_external_archive_pin_fails_before_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "no.zip"
            with self.assertRaisesRegex(audit.AuditError, "EXTERNAL_ARCHIVE_PIN_REQUIRED"):
                audit.audit_zip(missing, expected_sha256="", expected_head="0" * 40)
            with self.assertRaisesRegex(audit.AuditError, "EXTERNAL_SOURCE_HEAD_REQUIRED"):
                audit.audit_zip(missing, expected_sha256="0" * 64, expected_head="")

    def test_non_native_or_promoted_report_cannot_pass(self):
        with self.assertRaisesRegex(audit.AuditError, "COHORT_IDENTITY_RED"):
            audit.audit_report({"status": "UTILITY_PASS"})
        with self.assertRaisesRegex(audit.AuditError, "RUNNER_PIN_RED"):
            audit.audit_report({"schema": "v13.run117dg.normalized_source_paired_native.v1",
                                "seed": 117061, "table_sha256": audit.TABLE_SHA256,
                                "runner_sha256": "0" * 64, "pins_unchanged": True})


if __name__ == "__main__":
    unittest.main()
