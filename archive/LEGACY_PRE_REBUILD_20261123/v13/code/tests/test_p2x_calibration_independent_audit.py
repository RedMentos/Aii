"""Adversarial independent review tests for P2X calibration native evidence."""
from __future__ import annotations
import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import p2x_calibration_independent_audit as audit
from scripts import p2x_calibration_instruction as original
from tests.test_p2x_calibration_instruction import synthetic_records


def fixture():
    inputs = original.plan()
    records = synthetic_records()
    score = original.score(records)
    receipt = {
        "schema": "v13.p2x.calibration_instruction_native.v1",
        "status": "P2X_CALIBRATION_NATIVE_DIAGNOSTIC_NO_GATE",
        "prereg_commit": "9352843a7ef6fb0eb7cc3307b98f12501e9685c2",
        "expected_calls": 360, "recorded_calls": 360,
        "process_reaped": True, "model_sha256_before": audit.MODEL_SHA,
        "model_sha256_after": audit.MODEL_SHA,
        "runtime_sha256_before": audit.RUNTIME_SHA,
        "runtime_sha256_after": audit.RUNTIME_SHA,
        "runner_binary_sha256_before": audit.BINARY_SHA,
        "runner_binary_sha256_after": audit.BINARY_SHA,
        "adapter_sha256": None, "age_authority": 0,
        "weight_updates": False, "ag6_approved": False,
        "jepa_weight": 0, "redmi_measured": False,
        "whole_system_complete": False,
    }
    return inputs, records, score, receipt


class IndependentAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = fixture()

    def test_independent_instruction_is_exactly_registered(self):
        self.assertEqual(audit.SYSTEM, original.SYSTEM)
        plan, oracle = audit.reconstruct()
        self.assertEqual(len(plan), 360)
        self.assertEqual(len(oracle), 36)
        self.assertEqual({v: list(oracle.values()).count(v)
                          for v in ("A", "B", "NONE")},
                         {"A": 12, "B": 12, "NONE": 12})

    def test_strict_json_parser(self):
        self.assertEqual(audit.parse('{"action":"A"}'), "A")
        for output in ("A", '{"action":"A","reason":"yes"}',
                       '{"action":1}', '["A"]', "garbage", None):
            self.assertEqual(audit.parse(output), "UNPARSEABLE")

    def test_recompute_all_unknown_independently(self):
        report = audit.audit_data(*self.valid)
        self.assertEqual(report["rows"], 360)
        self.assertEqual(report["per_arm"]["original"]["both_exact"]["unknown"], 36)
        self.assertEqual(report["paired"]["both_exact"]["both_wrong"], 36)
        self.assertEqual(report["paired"]["shuffled"]["both_correct"], 36)
        self.assertEqual(report["step2_status"], "UTILITY_FAIL")

    def test_synthetic_paired_improvement_is_descriptive_only(self):
        inputs, records, _, receipt = copy.deepcopy(self.valid)
        oracle = audit.reconstruct()[1]
        for rec in records:
            if rec["arm"] == "both_exact" and rec["format"] == "instructed":
                rec["output"] = json.dumps({"action": oracle[rec["id"]]})
        score = original.score(records)
        report = audit.audit_data(inputs, records, score, receipt)
        self.assertEqual(report["paired"]["both_exact"]["improved"], 36)
        self.assertFalse(report["whole_system_complete"])

    def test_reject_score_forgery_and_gate_promotion(self):
        for path, value in ((("per_arm", "original", "both_exact", "exact"), 36),
                            (("details",), []),
                            (("step2_status",), "PASS"),
                            (("ag6_approved",), True)):
            with self.subTest(path=path):
                inputs, records, score, receipt = copy.deepcopy(self.valid)
                target = score
                for part in path[:-1]:
                    target = target[part]
                target[path[-1]] = value
                with self.assertRaisesRegex(ValueError, "SCORE_REPLAY"):
                    audit.audit_data(inputs, records, score, receipt)

    def test_reject_input_and_raw_tamper(self):
        for field, value in (("input_sha256", "0" * 64),
                             ("adapter_sha256", "forged"),
                             ("model_sha256", "0" * 64),
                             ("duration_s", 100),
                             ("status", "PARTIAL")):
            with self.subTest(field=field):
                inputs, records, score, receipt = copy.deepcopy(self.valid)
                records[0][field] = value
                with self.assertRaisesRegex(ValueError, "RAW_IDENTITY"):
                    audit.audit_data(inputs, records, score, receipt)
        inputs, records, score, receipt = copy.deepcopy(self.valid)
        inputs[0]["messages"][0]["content"] += "A"
        with self.assertRaisesRegex(ValueError, "INPUT_BINDING"):
            audit.audit_data(inputs, records, score, receipt)

    def test_reject_reorder_and_receipt_false_claims(self):
        inputs, records, score, receipt = copy.deepcopy(self.valid)
        records[0], records[1] = records[1], records[0]
        with self.assertRaisesRegex(ValueError, "RAW_ORDER"):
            audit.audit_data(inputs, records, score, receipt)
        inputs, records, score, receipt = copy.deepcopy(self.valid)
        receipt["weight_updates"] = True
        with self.assertRaisesRegex(ValueError, "RECEIPT_GATE"):
            audit.audit_data(inputs, records, score, receipt)

    def test_directory_replay_and_byte_hash_guard(self):
        inputs, records, score, receipt = copy.deepcopy(self.valid)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, data in (("INPUTS.json", inputs), ("RAW.json", records),
                               ("SCORE.json", score)):
                (root / name).write_bytes(audit.canonical(data))
                receipt[name.split(".")[0].lower() + "_sha256"] = (
                    audit.file_sha(root / name))
            (root / "RECEIPT.json").write_bytes(audit.canonical(receipt))
            self.assertEqual(audit.audit_directory(root)["rows"], 360)
            (root / "RAW.json").write_text("[]")
            with self.assertRaisesRegex(ValueError, "FILE_SHA"):
                audit.audit_directory(root)


if __name__ == "__main__":
    unittest.main()
