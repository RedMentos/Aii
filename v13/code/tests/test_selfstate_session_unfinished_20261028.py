"""Synthetic F3 SelfState session isolation for unfinished digital actions."""
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime


class SelfStateSessionUnfinished(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def pending(self, label):
        r = self.r
        event = r.store.event(r.session, label)
        forecast = r.world.forecast(event, "C3_LANGUAGE", native_prediction=False)
        return r.store.start_action(event["event_id"], r.store.generation_id, forecast=forecast)

    def count(self):
        return self.r.world.self_state()["unfinished_actions"]

    def test_old_session_pending_does_not_appear_in_new_self_state(self):
        old_session = self.r.session
        old_aid = self.pending("Unfinished action in old session")
        self.assertEqual(self.count(), 1)

        new_session = self.r.store.new_session()
        self.r.session = new_session
        self.assertNotEqual(old_session, new_session)
        self.assertEqual(self.count(), 0)

        new_aid = self.pending("Unfinished action in current session")
        self.assertEqual(self.count(), 1)
        self.r.session = old_session
        self.assertEqual(self.count(), 1)
        self.r.session = new_session
        self.r.store.finish_action(new_aid, "FINAL", {
            "role": "C3_LANGUAGE", "action_duration_s": 1.0,
        })
        self.assertEqual(self.count(), 0)
        self.r.session = old_session
        self.assertEqual(self.count(), 1)
        self.assertIsNotNone(self.r.store.one(
            "SELECT id FROM actions WHERE id=? AND status='DISPATCHED'", (old_aid,)
        ))

    def test_outcome_unknown_counts_only_own_session_after_restart(self):
        old_session = self.r.session
        old_aid = self.pending("Unknown action in old session")
        with self.r.store.tx() as db:
            db.execute("UPDATE actions SET status='OUTCOME_UNKNOWN' WHERE id=?", (old_aid,))
        self.assertEqual(self.count(), 1)

        new_session = self.r.store.new_session()
        self.r.session = new_session
        self.assertEqual(self.count(), 0)
        self.r.close()
        self.r = Runtime(self.home)
        self.assertEqual(self.r.session, new_session)
        self.assertEqual(self.count(), 0)
        self.r.session = old_session
        self.assertEqual(self.count(), 1)


if __name__ == "__main__":
    unittest.main()
