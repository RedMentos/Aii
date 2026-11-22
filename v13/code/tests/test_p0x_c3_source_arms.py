"""P0X preregistered 600 C3 source-arm software tests; no model calls."""
from unittest.mock import patch
import unittest

from scripts import p0x_c3_source_arms as arms
from scripts import p0x_c3_150_baseline as baseline
from scripts import hb1a_two_body_native_pilot as hb1


class P0XSourceArmsSoftware(unittest.TestCase):
    def fake_records(self, plan):
        return [
            {"id": p["id"], "arm": p["arm"], "status": "FINAL",
             "model_called": True, "native_calls": 1, "seed": arms.SEED,
             "model_sha256": arms.C3_MODEL_SHA256,
             "input_sha256": hb1.sha(hb1.canonical(p["messages"])),
             "schema_sha256": hb1.sha(hb1.canonical(p["schema"])),
             "output": '{"action":"NONE"}', "duration_s": .5,
             "metrics": {"status": "FINAL"}} for p in plan]

    def test_600_source_views_150_unique_ids_no_oracle(self):
        plan, answers = arms.plan_and_answers()
        self.assertEqual(len(plan), 600)
        self.assertEqual(len(answers), 150)
        self.assertEqual(len({(p["id"], p["arm"]) for p in plan}), 600)
        self.assertEqual([p["arm"] for p in plan[:4]], list(arms.ARMS))
        for p in plan:
            raw = hb1.canonical(p["messages"]).decode()
            for forbidden in ("oracle_action", "sheet_index", "rule_index",
                              "max_first", "max_second"):
                self.assertNotIn(forbidden, raw)
            self.assertEqual(p["messages"][0]["content"], hb1.C3_SYSTEM)

    def test_score_and_baseline_comparison_no_gate(self):
        plan, answers = arms.plan_and_answers()
        score = arms.score(self.fake_records(plan), plan, answers)
        self.assertTrue(all(v["exact"] == 50 and v["wrong_committed"] == 100
                            for v in score["per_arm"].values()))
        self.assertFalse(score["canonical_gate_pass"])
        base_plan, base_answers = baseline.plan_and_answers()
        base_records = [
            {"id": p["id"], "status": "FINAL", "model_called": True,
             "native_calls": 1, "seed": baseline.SEED,
             "model_sha256": baseline.C3_MODEL_SHA256,
             "input_sha256": hb1.sha(hb1.canonical(p["messages"])),
             "schema_sha256": hb1.sha(hb1.canonical(p["schema"])),
             "output": '{"action":"NONE"}', "duration_s": .5,
             "metrics": {"status": "FINAL"}} for p in base_plan]
        base_score = baseline.score(base_records, base_plan, base_answers)
        compared = arms.compare_to_baseline(score, base_score)
        self.assertEqual(compared["improvement"], 0)
        self.assertFalse(compared["threshold_met"])
        self.assertFalse(compared["both_exceeds_singles"])
        self.assertFalse(compared["canonical_gate_pass"])

    def test_tamper_and_missing_headroom_fail_closed(self):
        plan, answers = arms.plan_and_answers()
        records = self.fake_records(plan)
        records[0]["input_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "P0X_ARMS_RAW_BINDING_RED"):
            arms.score(records, plan, answers)
        records = self.fake_records(plan)
        records[0]["arm"] = records[1]["arm"]
        with self.assertRaisesRegex(ValueError, "P0X_ARMS_RAW_IDENTITY_RED"):
            arms.score(records, plan, answers)
        score = arms.score(self.fake_records(plan), plan, answers)
        with self.assertRaisesRegex(ValueError, "P0X_ARMS_BASELINE_HEADROOM_RED"):
            arms.compare_to_baseline(score, {"schema": baseline.SCHEMA + ".score.v1",
                                             "rows": 150, "c3_native_calls": 150,
                                             "headroom_sufficient": False,
                                             "oracle_headroom": 0})


if __name__ == "__main__":
    unittest.main()
