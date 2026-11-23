"""Explicitly rated model answers must not train from deleted/tampered/foreign sources.

Real SQLite Store and user-authored fixture; no model training or native claim.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.inputs import record_rating
from v13.agi.weights import WeightConsolidation


class RatedSourceAdmission(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.s = self.runtime.store

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def _rated(self, assistant_session=None):
        event = self.s.event(self.runtime.session, "What is the approved budget?")
        eid = event["event_id"]
        self.s.message(assistant_session or self.runtime.session, eid, "assistant",
                       "The budget is 120 EUR.", "FINAL", {"model_generated": True})
        record_rating(self.s, eid, 9, "EXPLICIT_NOTE")
        return eid, event["source_ref"]

    def _candidates(self):
        return WeightConsolidation(self.s, self.runtime.cfg).rated_candidates()

    def test_valid_explicit_rating_keeps_exact_source_ref_and_quality_only_label(self):
        eid, ref = self._rated()
        candidates = self._candidates()
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["event_id"], eid)
        self.assertEqual(candidates[0]["prompt"], "What is the approved budget?")
        self.assertEqual(candidates[0]["target"], "The budget is 120 EUR.")
        for field in ("source_id", "sha256", "char_start", "char_end", "modality"):
            self.assertEqual(candidates[0]["source_ref"][field], ref[field])
        self.assertEqual(candidates[0]["source_ref"]["label"], "HUMAN_QUALITY_LABEL_NOT_FACT")

    def test_revoked_source_never_returns_rated_candidate(self):
        _, ref = self._rated()
        self.assertEqual(len(self._candidates()), 1)
        with self.s.tx() as conn:
            conn.execute("UPDATE sources SET deleted=1 WHERE id=?", (ref["source_id"],))
        self.assertEqual(self._candidates(), [])

    def test_mutated_user_message_cannot_replace_original_source(self):
        eid, _ = self._rated()
        with self.s.tx() as conn:
            conn.execute("UPDATE messages SET text='Forged budget 999 EUR' "
                         "WHERE event_id=? AND role='user'", (eid,))
        self.assertEqual(self._candidates(), [])

    def test_foreign_session_assistant_cannot_form_rated_pair(self):
        foreign = self.s.new_session("Foreign session")
        self._rated(assistant_session=foreign)
        self.assertEqual(self._candidates(), [])


if __name__ == "__main__":
    unittest.main()
