"""Preregistered JEF report decision-lineage tests; synthetic real Store, no native."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from v13 import fastpolicy as fp
from v13 import jefoutcome as jo
from v13.runtime import Runtime


class JefReportDecisionBindingRun11H(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.e = self._event("synthetic first memory decision")
        self.r.memory.feedback(self.e["event_id"], "memory", "skip", "record")
        self.assertEqual(
            jo.after_turn(self.r, self.e, {"memory_ids": ["m1"]}, "FINAL",
                          {"coalition": []}), {"memory": "skip"})
        self.assertEqual(self.head()["human_overlap"], 1)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _event(self, text):
        event = self.r.store.event(self.r.session, text)
        fp.head(self.r, "memory", event, "recall")
        self.r.store.message(self.r.session, event["event_id"],
                             "assistant", "synthetic final", status="FINAL")
        return event

    def head(self):
        return jo.report(self.r)["heads"]["memory"]

    def _mutate(self, field, value):
        state, version = self.r.store.state(jo.KEY)
        labels = [x for x in state["labels"]
                  if x["event_id"] == self.e["event_id"]
                  and x["component"] == "memory"]
        self.assertEqual(len(labels), 1)
        labels[0][field] = value
        self.r.store.set_state(jo.KEY, state, expected=version)

    def assert_no_false_agreement(self):
        head = self.head()
        self.assertEqual(head["labels"], 1)
        self.assertEqual(head["live_labels"], 1)
        self.assertEqual(head["by_value"], {"skip": 1})
        self.assertEqual(head["human_overlap"], 0)
        self.assertIsNone(head["human_agreement"])
        self.assertEqual(self.r.pool.pids(), [])

    def test_untampered_receipt_has_real_human_agreement(self):
        head = self.head()
        self.assertEqual(head["labels"], 1)
        self.assertEqual(head["live_labels"], 1)
        self.assertEqual(head["human_overlap"], 1)
        self.assertEqual(head["human_agreement"], 1.0)

    def test_cross_event_valid_decision_substitution_must_not_count(self):
        second = self._event("synthetic second memory decision")
        self.r.memory.feedback(second["event_id"], "memory", "skip", "record")
        decision = jo._decision(self.r.store, second["event_id"], "memory")
        self.assertIsNotNone(decision)
        self._mutate("decision_packet_id", decision["packet_id"])
        self.assert_no_false_agreement()

    def test_label_event_mismatch_must_not_count(self):
        self._mutate("event_id", "different-event-id")
        self.assert_no_false_agreement()

    def test_label_context_digest_mismatch_must_not_count(self):
        self._mutate("context_sha256", "0" * 64)
        self.assert_no_false_agreement()

    def test_label_context_revision_mismatch_must_not_count(self):
        self._mutate("context_revision", "unrelated-revision")
        self.assert_no_false_agreement()

    def test_label_baseline_mismatch_must_not_count(self):
        self._mutate("baseline", "deep")
        self.assert_no_false_agreement()


if __name__ == "__main__":
    unittest.main()
