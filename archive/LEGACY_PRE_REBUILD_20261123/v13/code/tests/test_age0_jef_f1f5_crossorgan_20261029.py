"""Age0 one-home F1/F5 exact correction + registered JEF SHADOW decision."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import p2x_disjoint_receiver_trainset as cohort
from v13.runtime import Runtime
from v13.operator import Operator


class Age0JefF1F5CrossOrganTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        self.row = next(x for x in cohort.fixtures()
                        if x["partition"] == "calibration")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def record(self, key, value):
        e = self.r.store.event(self.r.session, "Record: " + key)
        mid = self.r.memory.feedback(
            e["event_id"], "fact", value,
            key=key, permission="record", scope="session")
        self.r.memory.candidate(mid, self.r.session)
        return mid

    def counts(self):
        return tuple(self.r.store.one(
            "SELECT COUNT(*) AS n FROM " + table)["n"]
            for table in ("sources", "events", "feedback", "packets", "memories"))

    def test_verified_exact_then_jef_shadow_uses_same_home_no_native(self):
        row = self.row
        project, domain = row["id"], row["domain"]
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("native model called")):
            source = json.loads(
                self.op.run(":source budget Elyra 615 --confirm"))
            self.assertEqual(source["status"], "RECORDED_VERIFIED")
            exact = json.loads(self.op.run(
                ":verified exact What is the budget for Project Elyra?"))
            self.assertEqual(exact["status"], "FINAL_SOURCE_EXACT")
            self.assertEqual(exact["answer"], "Project Elyra: 615 Euro.")
            self.assertEqual(exact["native_calls"], 0)

            policy = self.record(
                f"Project {project} archived {domain} policy",
                row["b2_source"])
            sheet = self.record(
                f"Project {project} latest {domain} option sheet",
                row["b1_source"])
            event = self.r.store.event(self.r.session, row["current"])
            before = self.counts()
            decision = json.loads(self.op.run(
                f":jefsource {event['event_id']} {policy} {sheet}"))
            self.assertEqual(decision["suggested_action"],
                             row["oracle_action"])
            self.assertEqual(decision["admission_status"],
                             "F1F5_SESSION_VERIFIED_SHADOW")
            self.assertEqual(decision["status"], "SHADOW_NO_AUTHORITY")
            self.assertTrue(decision["no_live_answer"])
            self.assertFalse(decision["model_called"])
            self.assertFalse(decision["weight_updates"])
            self.assertFalse(decision["ag6_approved"])
            self.assertEqual(decision["native_calls"], 0)
            self.assertEqual(decision["jepa_weight"], 0)
            self.assertEqual(self.counts(), before)

        self.assertEqual(self.r.cfg["system_stage"], 0)
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")
        self.assertIs(self.r.cfg["latents_enabled"], False)
        self.assertEqual(self.r.pool.pids(), [])


if __name__ == "__main__":
    unittest.main()
