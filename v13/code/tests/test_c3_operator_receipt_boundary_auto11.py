"""Adversarial native receipt admission tests; stubbed software only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import listarith_de_operator_shadow as cli


class NativeReceiptBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "input.txt"
        self.out = self.root / "report.json"
        self.source.write_text(
            "Inventar: Dohle 7, Esche 12, Falke 9. Wie hoch ist die Summe?",
            encoding="utf-8")
        self.raw = json.dumps({"values": [
            {"name": "Dohle", "number": 7},
            {"name": "Esche", "number": 12},
            {"name": "Falke", "number": 9}]}, sort_keys=True)

    def good_receipt(self):
        return {
            "native_attempted": True, "native_final": True,
            "postclose_process_reaped": True, "native_pid": 12345,
            "native_metrics": {"status": "FINAL"},
            "release": {"process_reaped": True},
            "error_type": None, "raw_output": self.raw,
        }

    def run_native_stub(self, receipt):
        with patch.object(cli, "_native_one", return_value=receipt):
            summary = cli.run(self.source, self.out, home=self.root)
        return summary, json.loads(self.out.read_text(encoding="utf-8"))

    def test_native_cannot_override_negative_gates_or_evidence_level(self):
        receipt = self.good_receipt()
        receipt.update({
            "evidence_level": "REDMI_PROVEN",
            "learning_mode": "APPROVED_COMMIT",
            "step2_gate_promoted": True, "b3_promoted": True,
            "body_jepa_available": True, "jepa_weight": 1,
            "redmi_measured": True, "whole_system_complete": True,
            "live_tool_execution": True, "external_action_authority": True,
        })
        summary, report = self.run_native_stub(receipt)
        self.assertEqual(summary["status"], "SHADOW_RESULT")
        self.assertEqual(report["evidence_level"], "LOCAL_NATIVE_IF_VERIFIED")
        self.assertEqual(report["learning_mode"], "RECORD_ONLY")
        for key in ("step2_gate_promoted", "b3_promoted",
                    "body_jepa_available", "redmi_measured",
                    "whole_system_complete", "live_tool_execution",
                    "external_action_authority"):
            self.assertIs(report[key], False, key)
        self.assertEqual(report["jepa_weight"], 0)

    def assert_quarantined(self, receipt, reason="NATIVE_RECEIPT_UNVERIFIED"):
        summary, report = self.run_native_stub(receipt)
        self.assertEqual(summary["status"], "SHADOW_ABSTAIN")
        self.assertEqual(report["status"], "SHADOW_ABSTAIN")
        self.assertEqual(report["reason"], reason)
        self.assertIsNone(report["baseline"])
        self.assertIsNone(report["closedworld"])
        self.assertIsNone(report["raw_output"])
        self.assertIsNone(report["raw_sha256"])
        self.assertEqual(report["quarantined_raw_sha256"],
                         hashlib.sha256(self.raw.encode("utf-8")).hexdigest())
        self.assertEqual(report["quarantined_raw_output"], self.raw)
        self.assertIs(report["native_receipt_admitted"], False)
        self.assertIs(report["step2_gate_promoted"], False)
        self.assertIs(report["whole_system_complete"], False)

    def test_raw_without_final_is_quarantined(self):
        receipt = self.good_receipt()
        receipt["native_final"] = False
        self.assert_quarantined(receipt)

    def test_raw_without_postclose_reap_is_quarantined(self):
        receipt = self.good_receipt()
        receipt["postclose_process_reaped"] = False
        self.assert_quarantined(receipt)

    def test_raw_without_pid_is_quarantined(self):
        receipt = self.good_receipt()
        receipt["native_pid"] = None
        self.assert_quarantined(receipt)

    def test_raw_without_release_proof_is_quarantined(self):
        receipt = self.good_receipt()
        receipt["release"] = {"process_reaped": False}
        self.assert_quarantined(receipt)

    def test_raw_with_error_is_quarantined(self):
        receipt = self.good_receipt()
        receipt["error_type"] = "NATIVE_RELEASE_RED"
        self.assert_quarantined(receipt)

    def test_good_stub_receipt_can_only_emit_shadow(self):
        summary, report = self.run_native_stub(self.good_receipt())
        self.assertEqual(summary["status"], "SHADOW_RESULT")
        self.assertEqual(report["closedworld"]["value"], 28)
        self.assertIs(report["native_receipt_admitted"], True)
        self.assertEqual(report["evidence_level"], "LOCAL_NATIVE_IF_VERIFIED")
        self.assertFalse(report["whole_system_complete"])

    def test_user_supplied_raw_replay_still_works(self):
        raw_file = self.root / "raw.json"
        raw_file.write_text(self.raw, encoding="utf-8")
        summary = cli.run(self.source, self.out, raw_json_file=raw_file)
        report = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "SHADOW_RESULT")
        self.assertEqual(report["closedworld"]["value"], 28)
        self.assertIs(report["native_attempted"], False)
        self.assertEqual(report["evidence_level"], "SOFTWARE_USER_SUPPLIED_RAW")


if __name__ == "__main__":
    unittest.main()
