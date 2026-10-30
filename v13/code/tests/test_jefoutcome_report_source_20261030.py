"""Preregistered JEF self-outcome report: only live, exact human receipt sources count."""
import tempfile
import unittest
from pathlib import Path

from v13 import fastpolicy as fp
from v13 import jefoutcome as jo
from v13.runtime import Runtime


class HumanOverlapSourceBinding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def labelled(self, human_value="skip"):
        e = self.r.store.event(self.r.session, "synthetic JEF report source")
        fp.head(self.r, "memory", e, "recall")
        self.r.store.message(self.r.session, e["event_id"], "assistant",
                             "Synthetic answer", status="FINAL")
        self.assertEqual(
            jo.after_turn(self.r, e, {"memory_ids": ["m1"]}, "FINAL",
                          {"coalition": []}),
            {"memory": "skip"})
        self.r.memory.feedback(e["event_id"], "memory", human_value, "learn")
        row = self.r.store.one(
            "SELECT source_id FROM feedback WHERE event_id=? AND kind='memory' "
            "ORDER BY created DESC LIMIT 1", (e["event_id"],))
        self.assertIsNotNone(row)
        return e, row["source_id"]

    def human(self):
        return jo.report(self.r)["heads"]["memory"]

    def test_live_matching_receipt_counts_agreement_and_disagreement(self):
        self.labelled()
        self.assertEqual(self.human()["human_overlap"], 1)
        self.assertEqual(self.human()["human_agreement"], 1.0)
        self.assertEqual(self.human()["labels"], 1)
        self.assertEqual(self.r.pool.pids(), [])

    def test_revoked_human_source_does_not_count_or_return_after_restart(self):
        _, source_id = self.labelled()
        self.assertEqual(self.human()["human_overlap"], 1)
        with self.r.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?", (source_id,))
        self.assertEqual(self.human()["human_overlap"], 0)
        self.assertIsNone(self.human()["human_agreement"])
        self.assertEqual(self.human()["labels"], 1)
        self.r.close()
        self.r = Runtime(self.home)
        self.assertEqual(self.human()["human_overlap"], 0)
        self.assertIsNone(self.human()["human_agreement"])

    def test_feedback_source_substitution_is_not_a_human_receipt(self):
        e, source_id = self.labelled()
        foreign = self.r.store.source("foreign synthetic source",
                                      "HUMAN_DECISION")["source_id"]
        self.assertNotEqual(source_id, foreign)
        with self.r.store.tx() as c:
            c.execute("UPDATE feedback SET source_id=? "
                      "WHERE event_id=? AND kind='memory'",
                      (foreign, e["event_id"]))
        self.assertEqual(self.human()["human_overlap"], 0)
        self.assertIsNone(self.human()["human_agreement"])
        self.assertEqual(self.human()["labels"], 1)

    def test_live_disagreement_is_still_measured(self):
        self.labelled(human_value="recall")
        self.assertEqual(self.human()["human_overlap"], 1)
        self.assertEqual(self.human()["human_agreement"], 0.0)


if __name__ == "__main__":
    unittest.main()
