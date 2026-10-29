"""Synthetic source-only checks for 16 training rows x 2 adapters; no model calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import p2x_json_train16_eval as M


def synthetic():
    prompts, answers = M.plan()
    oracle = {r["id"]: r["target_action"] for r in answers}
    records = [
        M.candidate.record_call(p, json.dumps({"action": oracle[p["id"]]}),
                                .01, {"status": "FINAL"}, M.ADAPTERS[p["arm"]])
        for p in prompts
    ]
    return prompts, answers, records


class JsonTrain16SourceOnly(unittest.TestCase):
    def test_plan_exact_frozen_training_only(self):
        prompts, answers = M.plan()
        self.assertEqual((len(prompts), len(answers)), (32, 16))
        self.assertEqual([p["arm"] for p in prompts],
                         ["bare"] * 16 + ["json"] * 16)
        self.assertEqual({a: sum(x["target_action"] == a for x in answers)
                          for a in M.resources.LABELS},
                         dict.fromkeys(M.resources.LABELS, 4))
        self.assertEqual({p["id"] for p in prompts}, {a["id"] for a in answers})
        self.assertEqual([p["messages"] for p in prompts[:16]],
                         [p["messages"] for p in prompts[16:]])
        self.assertEqual(M.EXPECTED, 32)
        self.assertNotEqual(M.ADAPTERS["bare"], M.ADAPTERS["json"])

    def test_synthetic_paired_positive_control_no_gate(self):
        prompts, answers, records = synthetic()
        score = M.score(records, prompts, answers)
        self.assertEqual(score["correct_in_sample"], {"bare": 16, "json": 16})
        self.assertEqual(score["paired_action_changes"], 0)
        self.assertEqual(score["native_calls"], 32)
        self.assertEqual((score["calibration_rows_used"],
                          score["validation_rows_used"]), (0, 0))
        self.assertEqual(score["step2_status"], "UTILITY_FAIL")
        self.assertFalse(score["ag6_approved"])
        self.assertFalse(score["whole_system_complete"])

    def test_adapter_swap_and_duplicate_rejected(self):
        prompts, answers, records = synthetic()
        records[0]["adapter_sha256"] = M.ADAPTERS["json"]
        with self.assertRaisesRegex(ValueError, "RAW_BINDING"):
            M.score(records, prompts, answers)
        prompts, answers, records = synthetic()
        records[1] = records[0].copy()
        with self.assertRaisesRegex(ValueError, "RAW_BINDING"):
            M.score(records, prompts, answers)

    def test_tampered_plan_or_raw_rejected(self):
        prompts, answers, records = synthetic()
        prompts[0]["messages"][0]["content"] += " target_action:A"
        with self.assertRaisesRegex(ValueError, "FROZEN_PLAN"):
            M.score(records, prompts, answers)
        prompts, answers, records = synthetic()
        records[0]["native_calls"] = 0
        with self.assertRaisesRegex(ValueError, "RAW_BINDING"):
            M.score(records, prompts, answers)

    def test_preflight_refuses_missing_pinned_assets(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            with self.assertRaisesRegex(ValueError, "BINARY_FILE"):
                M.preflight(p / "missing", p / "runtime", p / "model",
                            p / "bare", p / "json", p / "fresh")

    def test_synthetic_loopback_replay_and_tamper(self):
        prompts, answers, _ = synthetic()
        labels = {M.sha(M.canonical(p["messages"])): a["target_action"]
                  for p, a in zip(prompts[:16], answers)}
        class FakeServer:
            def __init__(self, binary, model, adapter, log):
                self.proc = None
                self.closed = False
            def generate(self, messages, timeout):
                return json.dumps({"action": labels[M.sha(M.canonical(messages))]}), {
                    "status": "FINAL"}
            def close(self):
                self.closed = True
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            paths = {"bare": p / "bare", "json": p / "json"}
            with patch.object(M, "preflight", return_value=(
                    p / "binary", p / "model", paths, prompts, answers,
                    {"synthetic": True})), patch.object(
                        M.candidate, "admit_file", side_effect=lambda path, *args: Path(path)):
                result = M.run_native(p / "binary", p / "runtime", p / "model",
                                      paths["bare"], paths["json"], p / "out",
                                      server_factory=FakeServer)
                self.assertEqual(result["recorded_calls"], 32)
                self.assertEqual(result["status"],
                                 "TRAINING_ONLY_NATIVE_DIAGNOSTIC_NO_GATE")
                replay = M.verify(p / "out")
                self.assertEqual(replay["correct_in_sample"],
                                 {"bare": 16, "json": 16})
                raw_path = p / "out" / "RAW.json"
                rows = json.loads(raw_path.read_text())
                rows[0]["adapter_sha256"] = "f" * 64
                raw_path.write_text(json.dumps(rows))
                with self.assertRaisesRegex(ValueError, "RAW_BINDING"):
                    M.verify(p / "out")


if __name__ == "__main__":
    unittest.main()
