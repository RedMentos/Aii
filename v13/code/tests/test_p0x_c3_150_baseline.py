"""P0X 150-row C3-only baseline plan/scorer software tests, no model calls."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from scripts import p0x_independent_source_holdout as p0x
from scripts import p0x_c3_150_baseline as base
from scripts import hb1a_two_body_native_pilot as hb1


class P0XC3BaselineSoftware(unittest.TestCase):
    def fake_records(self, plan):
        return [
            {"id": p["id"], "status": "FINAL", "model_called": True,
             "native_calls": 1, "seed": base.SEED,
             "model_sha256": base.C3_MODEL_SHA256,
             "input_sha256": hb1.sha(hb1.canonical(p["messages"])),
             "schema_sha256": hb1.sha(hb1.canonical(p["schema"])),
             "output": '{"action":"NONE"}', "duration_s": .5,
             "metrics": {"status": "FINAL"}} for p in plan]

    def test_plan_150_only_current_and_no_oracle(self):
        plan, answers = base.plan_and_answers()
        self.assertEqual(len(plan), 150)
        self.assertEqual(len(answers), 150)
        self.assertEqual({a["oracle_action"] for a in answers}, {"A", "B", "NONE"})
        for p in plan:
            self.assertEqual(p["messages"][0]["content"], hb1.C3_SYSTEM)
            self.assertEqual(p["messages"][1]["role"], "user")
            raw = hb1.canonical(p["messages"]).decode()
            for forbidden in ("oracle_action", "B1 exact source", "B2 exact source",
                              "FOREIGN B1 source", "sheet_index", "rule_index"):
                self.assertNotIn(forbidden, raw)

    def test_150_none_outputs_headroom_is_100_no_gate(self):
        plan, answers = base.plan_and_answers()
        score = base.score(self.fake_records(plan), plan, answers)
        self.assertEqual(score["per_arm"]["c3_only"]["exact"], 50)
        self.assertEqual(score["per_arm"]["c3_only"]["wrong_committed"], 100)
        self.assertEqual(score["oracle_headroom"], 100)
        self.assertTrue(score["headroom_sufficient"])
        self.assertEqual(score["output_labels"]["NONE"], 150)
        self.assertFalse(score["canonical_gate_pass"])
        self.assertEqual(score["step2_status"], "UTILITY_FAIL")
        self.assertFalse(score["whole_system_complete"])

    def test_wrong_fixture_and_raw_tamper_refused(self):
        with patch.object(base, "FIXTURE_SHA256", "0" * 64):
            with self.assertRaisesRegex(ValueError, "P0X_BASELINE_FIXTURE_DRIFT_RED"):
                base.plan_and_answers()
        plan, answers = base.plan_and_answers()
        records = self.fake_records(plan)
        records[0]["input_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "P0X_BASELINE_RAW_BINDING_RED"):
            base.score(records, plan, answers)
        records = self.fake_records(plan)
        records[0]["id"] = records[1]["id"]
        with self.assertRaisesRegex(ValueError, "P0X_BASELINE_IDENTITY_RED"):
            base.score(records, plan, answers)
        records = self.fake_records(plan)
        records[0]["duration_s"] = float("nan")
        with self.assertRaisesRegex(ValueError, "P0X_BASELINE_LATENCY_RED"):
            base.score(records, plan, answers)

    def test_unknown_and_unparseable_count_separately(self):
        plan, answers = base.plan_and_answers()
        records = self.fake_records(plan)
        records[0]["output"] = '{"action":"UNKNOWN"}'
        records[1]["output"] = "not json"
        score = base.score(records, plan, answers)
        self.assertEqual(score["per_arm"]["c3_only"]["unknown"], 1)
        self.assertEqual(score["per_arm"]["c3_only"]["unparseable"], 1)
        self.assertEqual(score["output_labels"]["UNKNOWN"], 1)
        self.assertEqual(score["output_labels"]["UNPARSEABLE"], 1)


if __name__ == "__main__":
    unittest.main()
