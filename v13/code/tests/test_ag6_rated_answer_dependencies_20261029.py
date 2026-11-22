"""AG6 must not stage a rated answer whose declared input dependencies were revoked.

Real SQLite Store-only negative controls. No native/model/learning execution.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.inputs import record_rating
from v13.agi.weights import WeightConsolidation


class RatedAnswerDependencyAdmission(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.s = self.r.store

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _rated(self, *, metadata=None, label="What is the budget?"):
        event = self.s.event(self.r.session, label)
        dependency = self.s.source("User-provided supporting context.", "HUMAN_FACT")
        if metadata is None:
            metadata = {"model_generated": True,
                        "context_source_refs": [event["source_ref"], dependency]}
        self.s.message(self.r.session, event["event_id"], "assistant",
                       "The budget is 120 EUR.", "FINAL", metadata)
        record_rating(self.s, event["event_id"], 9, "EXPLICIT_NOTE")
        return event, dependency

    def _ids(self):
        return [r["event_id"] for r in WeightConsolidation(
            self.s, self.r.cfg).rated_candidates()]

    def test_valid_source_bound_answer_is_eligible(self):
        event, _ = self._rated()
        self.assertEqual(self._ids(), [event["event_id"]])

    def test_revoked_answer_dependency_is_not_a_weight_candidate(self):
        event, dependency = self._rated()
        self.assertEqual(self._ids(), [event["event_id"]])
        with self.s.tx() as conn:
            conn.execute("UPDATE sources SET deleted=1 WHERE id=?",
                         (dependency["source_id"],))
        self.assertEqual(self._ids(), [])
        self.assertIsNotNone(self.s.one(
            "SELECT id FROM messages WHERE event_id=? AND role='assistant'",
            (event["event_id"],)))

    def test_malformed_declared_answer_dependency_is_not_admitted(self):
        event = self.s.event(self.r.session, "What is the budget?")
        self.s.message(self.r.session, event["event_id"], "assistant",
                       "The budget is 120 EUR.", "FINAL",
                       {"model_generated": True,
                        "context_source_refs": [{"source_id": "missing"}]})
        record_rating(self.s, event["event_id"], 9, "EXPLICIT_NOTE")
        self.assertEqual(self._ids(), [])

    def test_duplicate_final_answer_is_not_ambiguous_training_target(self):
        event, _ = self._rated()
        self.s.message(self.r.session, event["event_id"], "assistant",
                       "Contradictory budget is 999 EUR.", "FINAL",
                       {"model_generated": True})
        self.assertEqual(self._ids(), [])

    def test_unrelated_valid_rating_survives_revoked_other_dependency(self):
        bad, dependency = self._rated(label="First question?")
        good, _ = self._rated(label="Second question?")
        with self.s.tx() as conn:
            conn.execute("UPDATE sources SET deleted=1 WHERE id=?",
                         (dependency["source_id"],))
        self.assertEqual(self._ids(), [good["event_id"]])
        self.assertNotIn(bad["event_id"], self._ids())


if __name__ == "__main__":
    unittest.main()
