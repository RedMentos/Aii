"""Adversarial source-only replay tests for P2X base360 native verifier."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "p2x_base360_verifier", ROOT / "scripts/p2x_base360_native_verifier.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
from tests.test_p2x_native_receiver_eval_scorer import fixture


def write_evidence(root):
    plan, answers, raw = fixture()
    score = v.scorer.score(raw, plan, answers)
    for name, obj in (("RAW.json", raw), ("SCORE.json", score),
                      ("INPUTS.json", plan), ("ANSWERS.json", answers)):
        (root / name).write_bytes(v.scorer.canonical(obj))
    receipt = {
        "schema": v.SCHEMA, "status": v.SUCCESS,
        "evidence_kind": "LINUX_NATIVE_QAD_C3_P2X_BASE_ONLY",
        "fixture_sha256": v.scorer.FIXTURE_SHA,
        "validation_inputs_sha256": v.scorer.INPUT_SHA,
        "validation_answers_sha256": v.scorer.ANSWER_SHA,
        "model_sha256_before": v.scorer.MODEL_SHA,
        "model_sha256_after": v.scorer.MODEL_SHA,
        "runtime_sha256_before": v.scorer.RUNTIME_SHA,
        "runtime_sha256_after": v.scorer.RUNTIME_SHA,
        "adapter_sha256": None, "seed": 13, "c3_sampling": "off",
        "expected_calls": 360, "recorded_calls": 360,
        "process_reaped": True, "weight_updates": False,
        "jepa_weight": 0, "redmi_measured": False,
        "canonical_gate_pass": False, "whole_system_complete": False,
    }
    for name, key in (("RAW.json", "raw_sha256"), ("SCORE.json", "score_sha256"),
                      ("INPUTS.json", "inputs_sha256"), ("ANSWERS.json", "answers_sha256")):
        receipt[key] = v.native.file_sha(root / name)
    (root / "RECEIPT.json").write_text(json.dumps(receipt))
    return plan, answers


class Base360VerifyTests(unittest.TestCase):
    def test_exact_replay_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan, answers = write_evidence(root)
            with patch.object(v.scorer, "load_validation", return_value=(plan, answers)):
                result = v.verify(root, root)
            self.assertEqual(result["rows"], 360)
            self.assertIsNone(result["adapter_sha256"])
            self.assertEqual(result["status"], "VERIFIED_BASE_ONLY_LINUX_NATIVE_NO_GATE")

    def test_raw_hash_tamper_red(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan, answers = write_evidence(root)
            with (root / "RAW.json").open("ab") as f:
                f.write(b" ")
            with patch.object(v.scorer, "load_validation", return_value=(plan, answers)):
                with self.assertRaisesRegex(ValueError, "HASH"):
                    v.verify(root, root)

    def test_score_forgery_with_rehashed_receipt_red(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan, answers = write_evidence(root)
            score = json.loads((root / "SCORE.json").read_text())
            score["per_arm"]["both_exact"]["exact"] = 999
            (root / "SCORE.json").write_bytes(v.scorer.canonical(score))
            receipt = json.loads((root / "RECEIPT.json").read_text())
            receipt["score_sha256"] = v.native.file_sha(root / "SCORE.json")
            (root / "RECEIPT.json").write_text(json.dumps(receipt))
            with patch.object(v.scorer, "load_validation", return_value=(plan, answers)):
                with self.assertRaisesRegex(ValueError, "REPLAY"):
                    v.verify(root, root)

    def test_gate_forgery_red(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan, answers = write_evidence(root)
            receipt = json.loads((root / "RECEIPT.json").read_text())
            receipt["redmi_measured"] = True
            (root / "RECEIPT.json").write_text(json.dumps(receipt))
            with patch.object(v.scorer, "load_validation", return_value=(plan, answers)):
                with self.assertRaisesRegex(ValueError, "GATE"):
                    v.verify(root, root)

    def test_missing_score_red(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan, answers = write_evidence(root)
            (root / "SCORE.json").unlink()
            with patch.object(v.scorer, "load_validation", return_value=(plan, answers)):
                with self.assertRaisesRegex(ValueError, "MISSING"):
                    v.verify(root, root)


if __name__ == "__main__":
    unittest.main()
