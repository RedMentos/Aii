"""HB1b preregistered C3 output-format source-only regression (no native calls)."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts import hb1a_two_body_native_pilot as hb1
from scripts import hb1b_c3_format_followup as hb1b
from tests.test_hb1a_native_executor_mock import HB1AOrchestrationSoftware, FakePool


class HB1BFormatSoftware(unittest.TestCase):
    def make_parent(self, root):
        mock = HB1AOrchestrationSoftware()
        home = mock.setup_home(root)
        FakePool.fail_at = None
        mock.run_with_mocks(home, root / "parent")
        return root / "parent"

    def make_records(self, plan):
        return [
            {"id": p["id"], "arm": p["arm"],
             "model_sha256": hb1b.C3_MODEL_SHA256,
             "input_sha256": hb1.sha(hb1.canonical(p["messages"])),
             "schema_sha256": hb1.sha(hb1.canonical(p["schema"])) if p["schema"] else None,
             "output": '{"action":"NONE"}' if p["schema"] else "NONE",
             "duration_s": 0.5, "metrics": {"status": "FINAL"},
             "model_called": True, "native_calls": 1, "seed": hb1b.SEED,
             "status": "FINAL"} for p in plan
        ]

    def test_four_source_matched_arms_no_oracle(self):
        with TemporaryDirectory() as tmp:
            plan = hb1b.build(self.make_parent(Path(tmp)))
            self.assertEqual(len(plan), 24)
            self.assertEqual([p["arm"] for p in plan[:4]], list(hb1b.ARMS))
            self.assertEqual(sum(p["schema"] is not None for p in plan), 12)
            for i in range(0, 24, 4):
                self.assertEqual(plan[i]["messages"][1], plan[i+1]["messages"][1])
                self.assertEqual(plan[i+2]["messages"][1], plan[i+3]["messages"][1])
                self.assertNotEqual(plan[i]["messages"][0], plan[i+1]["messages"][0])
                for p in plan[i:i+4]:
                    self.assertNotIn("oracle_action", json.dumps(p))
                    self.assertNotIn("sheet_index", json.dumps(p))

    def test_parent_raw_hash_and_tamper_refused(self):
        with TemporaryDirectory() as tmp:
            root = self.make_parent(Path(tmp))
            raw_path = root / "RAW.json"
            raw = json.loads(raw_path.read_bytes())
            raw["body_rows"][0]["output"] = "CORRUPTED"
            raw_path.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ValueError, "HB1A_VERIFY_HASH_RED"):
                hb1b.build(root)

    def test_score_is_negative_gate_and_strict(self):
        with TemporaryDirectory() as tmp:
            plan = hb1b.build(self.make_parent(Path(tmp)))
            records = self.make_records(plan)
            score = hb1b.score(records, plan)
            self.assertEqual(score["rows"], 24)
            self.assertTrue(all(v["exact"] == 2 and v["wrong_committed"] == 4
                                for v in score["per_arm"].values()))
            self.assertFalse(score["canonical_gate_pass"])
            self.assertEqual(score["step2_status"], "UTILITY_FAIL")
            self.assertFalse(score["whole_system_complete"])
            self.assertEqual(hb1b.parse("I choose NONE", "exact_plain"), "UNPARSEABLE")
            self.assertEqual(hb1b.parse('{"action":"NONE"}', "exact_plain"), "UNPARSEABLE")
            self.assertEqual(hb1b.parse("NONE", "exact_schema"), "UNPARSEABLE")
            self.assertEqual(hb1b.parse("NONE\n", "exact_plain"), "NONE")

    def test_input_schema_identity_and_nonfinite_refused(self):
        with TemporaryDirectory() as tmp:
            plan = hb1b.build(self.make_parent(Path(tmp)))
            records = self.make_records(plan)
            records[0]["input_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "HB1B_RAW_BINDING_RED"):
                hb1b.score(records, plan)
            records = self.make_records(plan)
            records[1]["schema_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "HB1B_RAW_BINDING_RED"):
                hb1b.score(records, plan)
            records = self.make_records(plan)
            records[2]["duration_s"] = float("nan")
            with self.assertRaisesRegex(ValueError, "HB1B_LATENCY_RED"):
                hb1b.score(records, plan)
            records = self.make_records(plan)
            records[2]["id"] = records[1]["id"]
            records[2]["arm"] = records[1]["arm"]
            with self.assertRaisesRegex(ValueError, "HB1B_RAW_IDENTITY_RED"):
                hb1b.score(records, plan)


if __name__ == "__main__":
    unittest.main()
