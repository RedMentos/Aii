"""Adversarial source-only checks for P2X one-factor C3 calibration diagnostic."""
from __future__ import annotations
import copy
import unittest

from scripts import p2x_calibration_instruction as cal


def synthetic_records(output='{"action":"UNKNOWN"}'):
    records = []
    for p in cal.plan():
        records.append({
            "id": p["id"], "arm": p["arm"], "format": p["format"],
            "input_sha256": cal.sha(cal.canonical(p["messages"])),
            "model_sha256": cal.MODEL_SHA,
            "runtime_sha256": cal.RUNTIME_SHA,
            "runner_binary_sha256": cal.BINARY_SHA,
            "adapter_sha256": None, "seed": cal.SEED, "status": "FINAL",
            "model_called": True, "native_calls": 1, "duration_s": 0.1,
            "metrics": {"status": "FINAL"}, "output": output,
        })
    return records


class P2XCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = cal.plan()
        cls.synthetic = synthetic_records()

    def test_calibration_is_disjoint_balanced_and_exact_360(self):
        _, selected = cal.calibration()
        self.assertEqual(len(selected), 36)
        self.assertEqual({r["partition"] for r in selected}, {"calibration"})
        self.assertEqual({a: sum(r["oracle_action"] == a for r in selected)
                          for a in ("A", "B", "NONE")}, {"A": 12, "B": 12, "NONE": 12})
        self.assertEqual(len(self.rows), 360)
        self.assertEqual(len({(p["id"], p["arm"], p["format"])
                              for p in self.rows}), 360)

    def test_one_factor_only_system_instruction(self):
        for i in range(0, len(self.rows), 2):
            original, instructed = self.rows[i:i + 2]
            self.assertEqual(original["format"], "original")
            self.assertEqual(instructed["format"], "instructed")
            self.assertEqual(original["messages"], instructed["messages"][1:])
            self.assertEqual(instructed["messages"][0],
                             {"role": "system", "content": cal.SYSTEM})
            self.assertEqual(len(original["messages"]), 1)
            self.assertEqual(len(instructed["messages"]), 2)

    def test_no_answer_key_in_model_inputs(self):
        for p in self.rows:
            text = cal.canonical(p["messages"]).decode()
            for forbidden in ("oracle_action", "target_action",
                              "max_first", "max_second"):
                self.assertNotIn(forbidden, text)

    def test_all_unknown_is_not_utility_pass(self):
        report = cal.score(self.synthetic)
        self.assertEqual(report["native_calls"], 360)
        for fmt in cal.FORMATS:
            self.assertEqual(report["per_arm"][fmt]["both_exact"]["unknown"], 36)
            self.assertEqual(report["per_arm"][fmt]["both_exact"]["exact"], 0)
            for arm in cal.ARMS:
                if arm != "both_exact":
                    self.assertEqual(report["per_arm"][fmt][arm]["exact"], 36)
        self.assertEqual(report["step2_status"], "UTILITY_FAIL")
        self.assertFalse(report["whole_system_complete"])

    def test_none_collapse_cannot_be_misread_as_reasoning(self):
        report = cal.score(synthetic_records('{"action":"NONE"}'))
        for fmt in cal.FORMATS:
            self.assertEqual(report["per_arm"][fmt]["both_exact"]["exact"], 12)
            self.assertEqual(report["per_arm"][fmt]["both_exact"]["wrong_committed"], 24)
            self.assertEqual(report["per_arm"][fmt]["shuffled"]["wrong_committed"], 36)

    def test_raw_reorder_and_duplicate_fail_closed(self):
        records = copy.deepcopy(self.synthetic)
        records[0], records[1] = records[1], records[0]
        with self.assertRaisesRegex(ValueError, "RAW_ORDER"):
            cal.score(records)
        records = copy.deepcopy(self.synthetic)
        records[1] = copy.deepcopy(records[0])
        with self.assertRaisesRegex(ValueError, "RAW_ORDER"):
            cal.score(records)

    def test_bad_source_hash_and_adapter_fail_closed(self):
        for field, bad in (("input_sha256", "0" * 64),
                           ("model_sha256", "0" * 64),
                           ("runtime_sha256", "0" * 64),
                           ("runner_binary_sha256", "0" * 64),
                           ("adapter_sha256", "fake.gguf"),
                           ("seed", 14)):
            with self.subTest(field=field):
                records = copy.deepcopy(self.synthetic)
                records[0][field] = bad
                with self.assertRaisesRegex(ValueError, "RAW_BINDING"):
                    cal.score(records)

    def test_nonfinal_duration_and_call_count_fail_closed(self):
        for field, bad in (("status", "PARTIAL"),
                           ("native_calls", 0),
                           ("duration_s", float("nan")),
                           ("duration_s", 91),
                           ("model_called", False),
                           ("metrics", {"status": "FAILED"})):
            with self.subTest(field=field):
                records = copy.deepcopy(self.synthetic)
                records[0][field] = bad
                with self.assertRaisesRegex(ValueError, "RAW_BINDING"):
                    cal.score(records)

    def test_strict_json_no_loose_label_parsing(self):
        records = copy.deepcopy(self.synthetic)
        records[0]["output"] = "UNKNOWN"
        report = cal.score(records)
        self.assertEqual(report["per_arm"]["original"]["c3_only"]["unparseable"], 1)
        self.assertEqual(report["output_labels"]["original"]["c3_only"]["UNPARSEABLE"], 1)

    def test_score_replay_rejects_forged_aggregates_and_gates(self):
        report = cal.score(self.synthetic)
        self.assertEqual(cal.verify_score(self.synthetic, report)["rows"], 360)
        for path, bad in ((("per_arm", "original", "both_exact", "exact"), 36),
                          (("step2_status",), "PASS"),
                          (("details",), [])):
            with self.subTest(path=path):
                fake = copy.deepcopy(report)
                node = fake
                for key in path[:-1]:
                    node = node[key]
                node[path[-1]] = bad
                with self.assertRaisesRegex(ValueError, "SCORE_REPLAY"):
                    cal.verify_score(self.synthetic, fake)

    def test_forged_plan_rejected(self):
        changed = copy.deepcopy(self.rows)
        changed[0]["messages"][0]["content"] += " A"
        with self.assertRaisesRegex(ValueError, "PLAN_TAMPER"):
            cal.score(self.synthetic, changed)


if __name__ == "__main__":
    unittest.main()
