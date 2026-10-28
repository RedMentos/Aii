"""Run29: a stable content hash must not hide changed Store event order.

Software-only real ephemeral SQLite Store. No model, Runtime or age authority.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run18_step2_balanced_controls as balanced
from scripts import run17_german_typed_shadow as german
from scripts import run23_store_typed_bridge_shadow as bridge
from v13.config import initialize
from v13.store import Store


class EventOrderRevalidation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        home = Path(self.tmp.name)
        initialize(home)
        self.store = Store(home)
        self.session = self.store.new_session()
        self.case = next(c for c in balanced.FIXTURES if c["id"] == "Veldora")
        events = [
            self.store.event(self.session, self.case["history"][0]),
            self.store.event(self.session, self.case["history"][2]),
            self.store.event(self.session, self.case["current"]),
        ]
        self.refs = dict(zip(("old", "sheet", "current"),
                             (e["event_id"] for e in events)))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def evaluate(self):
        return bridge.evaluate(self.store, self.session, self.case["id"],
                               self.refs, self.case["temporal_mode"], "sheet")

    def test_clean_store_remains_shadow_only(self):
        out = self.evaluate()
        self.assertEqual(out["action"], self.case["oracle"]["action"])
        self.assertEqual(out["status"], "SHADOW_ONLY")
        self.assertIs(out["authority"], False)
        self.assertIs(out["canonical_gate_pass"], False)

    def test_reject_reordered_event_with_unchanged_content_hash(self):
        old_seq = self.store.one("SELECT rowid AS seq FROM events WHERE id=?",
                                 (self.refs["old"],))["seq"]
        current_seq = self.store.one("SELECT rowid AS seq FROM events WHERE id=?",
                                     (self.refs["current"],))["seq"]
        self.assertLess(old_seq, current_seq)
        old_hash = self.store.one(
            "SELECT s.hash FROM events e JOIN sources s ON s.id=e.source_id "
            "WHERE e.id=?", (self.refs["old"],))["hash"]
        original = german.evaluate

        def reorder_after_typed_evaluation(*args, **kwargs):
            result = original(*args, **kwargs)
            with self.store.tx() as db:
                db.execute("UPDATE events SET rowid=? WHERE id=?",
                           (current_seq + 1000, self.refs["old"]))
            return result

        with patch.object(german, "evaluate", reorder_after_typed_evaluation):
            with self.assertRaises(bridge.Refusal):
                self.evaluate()

        after = self.store.one(
            "SELECT e.rowid AS seq,s.hash FROM events e "
            "JOIN sources s ON s.id=e.source_id WHERE e.id=?",
            (self.refs["old"],))
        self.assertGreater(after["seq"], current_seq)
        self.assertEqual(after["hash"], old_hash)


if __name__ == "__main__":
    unittest.main()
