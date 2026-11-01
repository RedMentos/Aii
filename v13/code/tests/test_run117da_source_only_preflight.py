"""Run117DA software-only frozen cohort and real SQLite preflight controls."""
import hashlib
import json
import unittest
from unittest.mock import patch

from scripts import run117da_disjoint_schema_fixture as f
from scripts import run117da_source_only_preflight as pre
from v13.common import dumps


class Run117DAFixture(unittest.TestCase):
    def test_registered_table_balanced_disjoint_and_strict(self):
        rows = f.fixtures()
        self.assertEqual(len(rows), 12)
        self.assertEqual(f.SEED, 117053)
        self.assertEqual(f.TABLE_SHA256,
                         "78ec82002dafa54bcd9bb09456a0351123d2974bf12222fa6b20794d44f2edfb")
        self.assertEqual([r["expected_for_offline_scorer_only"] for r in rows],
                         ["A", "B", "NONE"] * 4)
        self.assertEqual(len(set(r["project"] for r in rows)), 12)
        for row in rows:
            self.assertEqual(row["source_sha256"]["current"],
                             hashlib.sha256(row["current"].encode()).hexdigest())
            self.assertTrue(f.strict('{"action":"'+row["expected_for_offline_scorer_only"]+'"}',
                                     row["expected_for_offline_scorer_only"]))
            self.assertFalse(f.strict("A", row["expected_for_offline_scorer_only"]))

    def test_order_rotates_balanced(self):
        rows = f.fixtures()
        for arm in f.ARMS:
            positions = [r["arm_order"].index(arm) for r in rows]
            self.assertEqual([positions.count(i) for i in range(4)], [3]*4)
        self.assertEqual(len({tuple(r["arm_order"]) for r in rows}), 4)

    def test_tamper_table_rejected_before_any_model(self):
        with patch.object(f, "TABLE", f.TABLE[:-1]):
            with self.assertRaisesRegex(ValueError, "TABLE_HASH_RED"):
                f.fixtures()

    def test_no_duplicate_project_or_prior_cohort_overlap(self):
        altered = (("Saffron",)+f.TABLE[0][1:],)+f.TABLE[1:]
        with patch.object(f, "TABLE", altered):
            with self.assertRaises(ValueError):
                f.fixtures()


class Run117DARealStorePreflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = pre.preflight()

    def test_real_store_all_twelve_no_native_and_no_oracle(self):
        r = self.result
        self.assertEqual(r["status"], pre.STATUS)
        self.assertEqual(r["planned_serial_native_calls"], 48)
        self.assertEqual(r["native_calls"], 0)
        self.assertEqual(len(r["rows"]), 12)
        for row, frozen in zip(r["rows"], f.fixtures()):
            self.assertTrue(row["store_closed"])
            self.assertEqual(row["source_sha256"], frozen["source_sha256"])
            self.assertEqual(row["arm_order"], frozen["arm_order"])
            self.assertEqual(row["native_calls"], 0)
            self.assertEqual(row["model_calls"], 0)
            self.assertFalse(row["oracle_visible_to_native"])
            self.assertFalse(row["typed_jef_action_visible"])
            self.assertEqual(row["messages_sha256"],
                             hashlib.sha256(dumps(row["messages"]).encode()).hexdigest())
            self.assertEqual([m["role"] for m in row["messages"]], ["system","user"])
            payload = json.loads(row["messages"][1]["content"])
            self.assertFalse(payload["typed_jef_action_visible"])
            self.assertNotIn("oracle", payload)
            self.assertNotIn("suggested_action", payload)
            self.assertNotIn("typed_jef_action", payload)
            self.assertEqual(payload["current"]["text"], frozen["current"])
            self.assertEqual(payload["policy"]["text"], frozen["policy_source"])
            self.assertEqual(payload["sheet"]["text"], frozen["sheet_source"])

    def test_negative_gates_and_exact_model_pins(self):
        r = self.result
        self.assertEqual(r["age0"], "RECORD_ONLY")
        self.assertEqual(r["step2"], "UTILITY_FAIL")
        self.assertEqual(r["b3"], "NO_PROMOTION")
        self.assertEqual(r["body_jepa"], "UNAVAILABLE")
        self.assertEqual(r["world_jepa"], "SHADOW")
        self.assertEqual(r["jepa_weight"], 0)
        self.assertFalse(r["whole_system_complete"])
        self.assertFalse(r["redmi_measured"])
        self.assertFalse(r["output_committed"])
        self.assertEqual([m["id"] for m in r["models"]],
                         ["lfm25_350m", "qwen35_0p8b"])

    def test_preflight_uses_no_runner(self):
        self.assertFalse(any("native_output" in row for row in self.result["rows"]))
        self.assertFalse(any("expected_for_offline_scorer_only" in row
                             for row in self.result["rows"]))


if __name__ == "__main__":
    unittest.main()
