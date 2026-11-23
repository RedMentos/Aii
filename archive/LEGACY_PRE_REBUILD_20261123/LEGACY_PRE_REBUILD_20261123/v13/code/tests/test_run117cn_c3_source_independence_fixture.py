"""Run117CN preregistered disjoint C3 source-independence software integrity."""
import collections
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run117cn_c3_source_independence_fixture as F
from scripts import jef_range_native_fixture_773 as prior
from scripts import jef_body_c3_interference_fixture_839 as run83
from tests.test_jef_range_policy_shadow import TABLE as RUN73_TABLE
from tests.test_run52_b1b2_cross_turn import FakeRuntime
from v13 import jef_c3_source_only_shadow_candidate as C


class C3SourceIndependenceFixture(unittest.TestCase):
    def test_frozen_table_balanced_disjoint_and_counterbalanced(self):
        rows = F.fixtures()
        self.assertEqual(len(rows), 9)
        self.assertEqual([r["expected_for_offline_scorer_only"] for r in rows],
                         ["A", "B", "NONE"] * 3)
        prior_projects = {r[0] for table in (RUN73_TABLE, prior.TABLE, run83.TABLE)
                          for r in table}
        self.assertFalse({r["project"] for r in rows} & prior_projects)
        self.assertEqual(len({r["project"] for r in rows}), 9)
        self.assertTrue(all(prior.oracle(row) == row[-1] for row in F.TABLE))
        positions = collections.Counter((arm, pos)
            for row in rows for pos, arm in enumerate(row["arm_order"]))
        self.assertEqual(set(positions.values()), {3})
        self.assertTrue(all(r["wrong_typed_action_synthetic_only"]
                            != r["expected_for_offline_scorer_only"] for r in rows))
        self.assertTrue(all(r["authority"] == 0 and r["native_calls"] == 0
                            and not r["whole_system_complete"] for r in rows))

    def test_table_tamper_fails_before_native(self):
        altered = (("FORGED",) + F.TABLE[0][1:],) + F.TABLE[1:]
        with patch.object(F, "TABLE", altered):
            with self.assertRaisesRegex(ValueError, "RUN117CN_TABLE_HASH_RED"):
                F.fixtures()

    def test_strict_json_only_no_partial_credit(self):
        self.assertEqual(F.strict('{"action":"A"}', "A"), 1)
        self.assertEqual(F.strict('{"action":"A","reason":"because"}', "A"), 0)
        self.assertEqual(F.strict('{"action":"B"}', "A"), 0)

    def test_all_nine_source_only_envelopes_are_human_bound_and_oracle_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            r = FakeRuntime(Path(d))
            try:
                for case in F.fixtures():
                    with self.subTest(project=case["project"]):
                        r.session = r.store.new_session()
                        ids = []
                        for key, text in (
                            (f"Project {case['project']} archived "
                             + next(row[1] for row in F.TABLE if row[0] == case["project"])
                             + " policy", case["policy_source"]),
                            (f"Project {case['project']} latest "
                             + next(row[1] for row in F.TABLE if row[0] == case["project"])
                             + " option sheet", case["sheet_source"]),
                        ):
                            event = r.store.event(r.session, "Record: " + key)
                            mid = r.memory.feedback(
                                event["event_id"], "fact", text,
                                permission="record", key=key, scope="session")
                            r.memory.candidate(mid, r.session)
                            ids.append(mid)
                        event = r.store.event(r.session, case["current"])
                        with patch.object(r.pool, "get",
                                          side_effect=AssertionError("NATIVE_CALLED")):
                            result = C.build(
                                r.memory, r.session, event["event_id"],
                                event["source_ref"], ids, operator_opt_in=True)
                        self.assertEqual(result["status"], C.STATUS, result)
                        payload = json.loads(result["messages"][1]["content"])
                        self.assertEqual(payload["current"]["text"], case["current"])
                        self.assertEqual(payload["policy"]["text"], case["policy_source"])
                        self.assertEqual(payload["sheet"]["text"], case["sheet_source"])
                        self.assertNotIn("typed_jef_action", payload)
                        self.assertNotIn("suggested_action", payload)
                        self.assertNotIn("expected_action", payload)
                        self.assertFalse(result["model_called"])
                        self.assertFalse(result["oracle_action_visible"])
                        self.assertFalse(result["independent_reasoning_proven"])
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
