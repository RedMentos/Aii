"""Software-only P2X CAL36 plan, receipt and replay regressions; no model calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import p2x_cal36_transport as M
from scripts import p2x_disjoint_receiver_trainset as fixture


def synthetic_records():
    prompts, answers = M.plan()
    oracle = {a["id"]: a["oracle_action"] for a in answers}
    records = []
    for prompt in prompts:
        action = oracle[prompt["id"]] if prompt["arm"] == "both_exact" else "UNKNOWN"
        records.append(M.candidate.record_call(
            prompt, json.dumps({"action": action}), .01, {"status": "FINAL"},
            M.ADAPTER_SHA))
    return prompts, answers, records


class FakeServer:
    instances = []
    fail_after = None
    lookup = {}
    def __init__(self, *args):
        self.calls = 0
        self.closed = False
        self.args = args
        self.__class__.instances.append(self)

    def generate(self, messages, timeout):
        if self.fail_after is not None and self.calls >= self.fail_after:
            raise RuntimeError("synthetic mid-run failure")
        self.calls += 1
        return json.dumps({"action": self.lookup[M.sha(M.canonical(messages))]}), {
            "status": "FINAL", "synthetic": True}

    def close(self):
        self.closed = True


def run_mocked(root, fail_after=None):
    prompts, answers, _ = synthetic_records()
    oracle = {a["id"]: a["oracle_action"] for a in answers}
    FakeServer.instances = []
    FakeServer.fail_after = fail_after
    FakeServer.lookup = {
        M.sha(M.canonical(p["messages"])):
            oracle[p["id"]] if p["arm"] == "both_exact" else "UNKNOWN"
        for p in prompts}
    paths = [root / x for x in ("binary", "archive", "model", "adapter")]
    with (patch.object(M.candidate, "admit_file",
                       side_effect=lambda path, sha, label: Path(path)),
          patch.object(M.resources, "resource_admission",
                       return_value={"memory_available_bytes": 6_000_000_000})):
        return M.run_native(*paths, root / "out", server_factory=FakeServer)


class Cal36Tests(unittest.TestCase):
    def test_frozen_partition_and_two_arm_no_oracle_leak(self):
        prompts, answers = M.plan()
        self.assertEqual((len(prompts), len(answers)), (72, 36))
        self.assertEqual([p["arm"] for p in prompts[:4]],
                         ["both_exact", "c3_only"] * 2)
        self.assertEqual({a: sum(r["oracle_action"] == a for r in answers)
                          for a in ("A", "B", "NONE")},
                         {"A": 12, "B": 12, "NONE": 12})
        rows = fixture.fixtures()
        calibration = {r["id"] for r in rows if r["partition"] == "calibration"}
        train = {r["id"] for r in rows if r["partition"] == "train"}
        validation = {r["id"] for r in rows if r["partition"] == "validation"}
        self.assertEqual(calibration, {a["id"] for a in answers})
        self.assertFalse(calibration & (train | validation))
        for p in prompts:
            text = p["messages"][0]["content"]
            for forbidden in ("oracle_action", "target_action", "max_first", "max_second"):
                self.assertNotIn(forbidden, text)

    def test_exact_positive_and_negative_controls_replay(self):
        prompts, answers, records = synthetic_records()
        score = M.score(records, prompts, answers)
        self.assertEqual(score["positive_correct"], 24)
        self.assertEqual(score["none_correct"], 12)
        self.assertEqual(score["negative_abstained"], 36)
        self.assertEqual(score["paired_source_sensitive"], 24)
        self.assertEqual(score["per_arm"]["both_exact"]["correct"], 36)
        self.assertEqual(score["per_arm"]["c3_only"]["correct"], 36)
        self.assertEqual(score["validation_rows_used"], 0)
        self.assertEqual(score["step2_status"], "UTILITY_FAIL")
        self.assertFalse(score["whole_system_complete"])
        wrong = copy.deepcopy(records)
        wrong[0]["output"] = '{"action":"NONE"}' if answers[0]["oracle_action"] != "NONE" else '{"action":"A"}'
        changed = M.score(wrong, prompts, answers)
        self.assertEqual(changed["per_arm"]["both_exact"]["wrong_committed"], 1)
        self.assertEqual(changed["paired_source_sensitive"],
                         23 if answers[0]["oracle_action"] in ("A", "B") else 24)

    def test_raw_tampering_and_duplicate_are_refused(self):
        prompts, answers, records = synthetic_records()
        cases = [("input_sha256", "0" * 64), ("seed", True),
                 ("adapter_sha256", "0" * 64), ("duration_s", float("nan")),
                 ("native_calls", True), ("status", "RUNNING")]
        for key, value in cases:
            with self.subTest(key=key):
                tampered = copy.deepcopy(records)
                tampered[0][key] = value
                with self.assertRaisesRegex(ValueError, "RAW_BINDING_RED"):
                    M.score(tampered, prompts, answers)
        duplicate = copy.deepcopy(records)
        duplicate[1] = duplicate[0]
        with self.assertRaisesRegex(ValueError, "RAW_BINDING_RED"):
            M.score(duplicate, prompts, answers)
        wrong_plan = copy.deepcopy(prompts)
        wrong_plan[0]["messages"][0]["content"] += " oracle_action:A"
        with self.assertRaisesRegex(ValueError, "FROZEN_PLAN_RED"):
            M.score(records, wrong_plan, answers)

    def test_mocked_72_calls_are_persisted_and_verifiable(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = run_mocked(root)
            self.assertEqual(result["recorded_calls"], 72)
            self.assertEqual(result["status"], "P2X_CAL36_NATIVE_DIAGNOSTIC_NO_GATE")
            self.assertTrue(FakeServer.instances[-1].closed)
            self.assertEqual(FakeServer.instances[-1].calls, 72)
            replay = M.verify(root / "out")
            self.assertEqual(replay["positive_correct"], 24)
            self.assertEqual(replay["negative_abstained"], 36)
            self.assertEqual(replay["paired_source_sensitive"], 24)
            self.assertFalse(replay["ag6_approved"])
            self.assertEqual(replay["jepa_weight"], 0)
            self.assertEqual(len(json.loads((root / "out" / "RAW.json").read_text())), 72)
            with self.assertRaisesRegex(ValueError, "FRESH_OUTPUT_RED"):
                run_mocked(root)

    def test_verify_rejects_score_receipt_and_raw_forgery(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run_mocked(root)
            out = root / "out"
            score_path = out / "SCORE.json"
            original_score = score_path.read_text()
            score = json.loads(original_score)
            score["positive_correct"] += 1
            score_path.write_text(json.dumps(score))
            with self.assertRaisesRegex(ValueError, "SCORE_REPLAY_RED"):
                M.verify(out)
            score_path.write_text(original_score)
            receipt_path = out / "RECEIPT.json"
            receipt = json.loads(receipt_path.read_text())
            receipt["canonical_gate_pass"] = True
            receipt_path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, "RECEIPT_GATE_RED"):
                M.verify(out)

    def test_midrun_failure_retains_original_raw_without_success(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaisesRegex(RuntimeError, "synthetic mid-run failure"):
                run_mocked(root, fail_after=3)
            self.assertTrue(FakeServer.instances[-1].closed)
            out = root / "out"
            receipt = json.loads((out / "RECEIPT.json").read_text())
            self.assertEqual(receipt["status"], "FAIL_RETAIN_RAW")
            self.assertEqual(receipt["recorded_calls"], 3)
            self.assertEqual(len(json.loads((out / "RAW.json").read_text())), 3)
            self.assertFalse((out / "SCORE.json").exists())
            self.assertFalse(receipt["canonical_gate_pass"])


if __name__ == "__main__":
    unittest.main()
