"""Adversarial independent paired109 audit tests; synthetic receipts only."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import c3_typedread_paired109_native as cohort
from scripts import c3_typedread_paired109_independent_audit as audit


class Paired109IndependentAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "synthetic_report.json"
        rows = cohort.frozen_rows()
        expected_by_text = {r["text"]: r["expected_values"] for r in rows}

        def fake_native(home, cfg, model_path, text, system):
            raw = json.dumps({"values": expected_by_text[text]})
            return {"native_attempted": True, "native_final": True,
                    "postclose_process_reaped": True, "native_pid": 12345,
                    "native_metrics": {"status": "FINAL",
                                       "actual_model": "LFM2.5-350M-QAD-Q4_0.gguf"},
                    "release": {"process_reaped": True}, "error_type": None,
                    "raw_output": raw, "admitted": True}

        with patch.object(cohort.operator, "_native_preflight",
                          return_value=(self.root, {}, self.root / "fake.gguf")), \
             patch.object(cohort, "native_read", side_effect=fake_native):
            cohort.run(self.root, self.path)
        self.original = json.loads(self.path.read_text(encoding="utf-8"))

    def audit_changed(self, mutation, expected_error):
        report = copy.deepcopy(self.original)
        mutation(report)
        self.path.write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaisesRegex(audit.AuditError, expected_error):
            audit.audit(self.path)

    def test_synthetic_fixture_passes_structural_audit_only(self):
        result = audit.audit(self.path)
        self.assertEqual(result["audit"], "STRUCTURAL_PASS")
        self.assertEqual(result["counts"]["D_exact"], 8)
        self.assertEqual(result["counts"]["A_exact"], 8)
        self.assertEqual(result["counts"]["B_exact"], 8)
        self.assertEqual(result["counts"]["native_admitted"], 16)
        self.assertEqual(result["diagnostic"]["A_wrong"], 0)
        self.assertFalse(result["whole_system_complete"])
        self.assertEqual(result["evidence_level"],
                         "LINUX_NATIVE_IF_ORIGINAL_ZIP_VERIFIED")

    def test_forged_count_rejected(self):
        self.audit_changed(lambda r: r["counts"].update(A_exact=7),
                           "REPORTED_COUNTS_CHANGED")

    def test_substituted_raw_rejected(self):
        self.audit_changed(
            lambda r: r["rows"][0]["arms"]["A"]["receipt"].update(
                raw_output='{"values":[]}'), "RAW_HASH_CHANGED")

    def test_unreaped_process_rejected(self):
        self.audit_changed(
            lambda r: r["rows"][0]["arms"]["B"]["receipt"].update(
                postclose_process_reaped=False), "NATIVE_RECEIPT_UNVERIFIED")

    def test_forged_gate_rejected(self):
        self.audit_changed(lambda r: r.update(step2_gate_promoted=True),
                           "NEGATIVE_GATE_CHANGED")

    def test_substituted_source_hash_rejected(self):
        self.audit_changed(
            lambda r: r["rows"][2].update(source_sha256="0"*64),
            "SOURCE_HASH_CHANGED")

    def test_substituted_closedworld_result_rejected(self):
        self.audit_changed(
            lambda r: r["rows"][1]["arms"]["B"]["closedworld"].update(
                value=999), "CLOSEDWORLD_CHANGED")

    def test_substituted_model_rejected(self):
        self.audit_changed(lambda r: r.update(model_sha256="0"*64),
                           "MODEL_CHANGED")


if __name__ == "__main__":
    unittest.main()
