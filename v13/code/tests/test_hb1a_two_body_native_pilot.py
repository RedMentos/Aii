"""HB1a synthetic plan/score controls; no native/model inference."""
from copy import deepcopy
import math
import unittest

from scripts import hb0_split_information_cohort as hb0
from scripts import hb1a_two_body_native_pilot as pilot


class HB1ASoftware(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = hb0.fixtures()
        cls.fixture = hb0._sha(cls.rows)
        cls.body = pilot.body_plan(cls.rows, cls.fixture)

    def mock_body(self):
        return [{"id": p["id"], "kind": p["kind"], "role": p["role"],
                 "source_project": p["source_project"],
                 "source_sha256": p["source_sha256"],
                 "input_sha256": pilot.sha(pilot.canonical(p["messages"])),
                 "model_sha256": pilot.MODEL_SHAS[p["role"]],
                 "output": "SOURCE QUOTE ONLY", "duration_s": 1.0,
                 "metrics": {"status": "FINAL"}, "seed": pilot.SEED,
                 "model_called": True, "native_calls": 1, "status": "FINAL"}
                for p in self.body]

    def mock_c3(self, body):
        prompts = pilot.receiver_plan(self.rows, self.fixture, body)
        return [{"id": p["id"], "arm": p["arm"],
                 "input_sha256": pilot.sha(pilot.canonical(p["messages"])),
                 "model_sha256": pilot.MODEL_SHAS["C3_LANGUAGE"],
                 "output": '{"action":"UNKNOWN"}', "duration_s": 1.0,
                 "metrics": {"status": "FINAL"}, "seed": pilot.SEED,
                 "model_called": True, "native_calls": 1, "status": "FINAL"}
                for p in prompts]

    def test_exact_24_body_plan_and_source_isolation(self):
        self.assertEqual(len(self.body), 24)
        self.assertEqual(len({p["id"] for p in self.body}), 6)
        for index in range(0, 24, 4):
            group = self.body[index:index + 4]
            self.assertEqual([p["kind"] for p in group], list(pilot.BODY_KINDS))
            self.assertEqual([p["role"] for p in group],
                             ["B1_DETAIL", "B2_GIST", "B1_DETAIL", "B1_DETAIL"])
            self.assertEqual(len({p["id"] for p in group}), 1)
            self.assertNotEqual(group[3]["source_project"], group[0]["id"])
            self.assertEqual(group[0]["source_project"], group[0]["id"])
            self.assertEqual(group[1]["source_project"], group[1]["id"])
            for p in group:
                self.assertNotIn("oracle_action", str(p))
                self.assertNotIn("sheet_index", str(p))
                self.assertNotIn("rule_index", str(p))
        self.assertEqual(pilot.BODY_TOKENS, 96)
        self.assertEqual(pilot.C3_TOKENS, 48)

    def test_30_c3_prompts_and_no_oracle(self):
        body = self.mock_body()
        prompts = pilot.receiver_plan(self.rows, self.fixture, body)
        self.assertEqual(len(prompts), 30)
        for index in range(0, 30, 5):
            group = prompts[index:index + 5]
            self.assertEqual([p["arm"] for p in group], list(pilot.C3_ARMS))
            self.assertEqual(len({p["id"] for p in group}), 1)
            self.assertNotIn("SOURCE QUOTE ONLY", str(group[0]))
            self.assertNotIn("SOURCE QUOTE ONLY", str(group[1]))
            self.assertIn("SOURCE QUOTE ONLY", str(group[2]))
            self.assertIn("FOREIGN CONTROL", str(group[4]))
            for p in group:
                self.assertNotIn("oracle_action", str(p))

    def test_external_pin_and_body_identity_refusal(self):
        with self.assertRaisesRegex(ValueError, "HB1A_EXTERNAL_FIXTURE_SHA_RED"):
            pilot.body_plan(self.rows, "0" * 64)
        body = self.mock_body()
        for field, value in (("source_project", "FORGED"),
                             ("input_sha256", "0" * 64),
                             ("model_sha256", "f" * 64),
                             ("seed", 17)):
            with self.subTest(field=field):
                bad = deepcopy(body)
                bad[0][field] = value
                with self.assertRaisesRegex(ValueError, "HB1A_BODY_RAW_TAMPER_RED"):
                    pilot.receiver_plan(self.rows, self.fixture, bad)
        with self.assertRaisesRegex(ValueError, "HB1A_BODY_RAW_COUNT_RED"):
            pilot.receiver_plan(self.rows, self.fixture, body[:-1])

    def test_strict_json_action_parser(self):
        for raw, expected in [
            ('{"action":"A"}', "A"),
            ('{"action":"B"}', "B"),
            ('{"action":"NONE"}', "NONE"),
            ('{"action":"UNKNOWN"}', "UNKNOWN"),
            ('{"action":"A","oracle":"A"}', "UNPARSEABLE"),
            ('{"action":"C"}', "UNPARSEABLE"),
            ('{"action":1}', "UNPARSEABLE"),
            ('Option A', "UNPARSEABLE"),
            (None, "UNPARSEABLE"),
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(pilot.parse_action(raw), expected)

    def test_synthetic_score_negative_gates_and_tamper(self):
        body = self.mock_body()
        c3 = self.mock_c3(body)
        report = pilot.score(body, c3, self.rows, self.fixture)
        self.assertEqual(report["rows"], 30)
        self.assertEqual(sum(v["unknown"] for v in report["per_arm"].values()), 30)
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_status"], "UTILITY_FAIL")
        self.assertEqual(report["b3_status"], "FAIL")
        self.assertEqual(report["jepa_weight"], 0)
        self.assertFalse(report["redmi_measured"])
        with self.assertRaisesRegex(ValueError, "HB1A_C3_RAW_COUNT_RED"):
            pilot.score(body, c3[:-1], self.rows, self.fixture)
        bad = deepcopy(c3)
        bad[0]["input_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "HB1A_C3_RAW_TAMPER_RED"):
            pilot.score(body, bad, self.rows, self.fixture)
        for t in (float("nan"), float("inf"), -1, True):
            with self.subTest(t=t):
                bad = deepcopy(c3)
                bad[0]["duration_s"] = t
                with self.assertRaisesRegex(ValueError, "HB1A_C3_LATENCY_RED"):
                    pilot.score(body, bad, self.rows, self.fixture)


if __name__ == "__main__":
    unittest.main()
