"""Run379: F4 SelfState must not count another chat's unfinished actions.

Actual Runtime/SQLite, synthetic local action receipts; no model or Redmi proof.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime


class WorldSelfStateSessionRun379(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.a = self.r.session

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def start(self, session, text):
        event = self.r.store.event(session, text)
        return self.r.store.start_action(event["event_id"], event["brain_generation_id"])

    def count(self, session):
        self.r.session = session
        state = self.r.world.self_state()
        self.assertEqual(state["session_id"], session)
        return state["unfinished_actions"]

    def test_cross_session_accounting_terminal_and_restart(self):
        a1 = self.start(self.a, "Session A local action")
        b = self.r.store.new_session()
        b1 = self.start(b, "Session B first action")
        b2 = self.start(b, "Session B second action")
        with self.r.store.tx() as db:
            db.execute("UPDATE actions SET status='OUTCOME_UNKNOWN' WHERE id=?", (b2,))
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM actions WHERE status IN ('DISPATCHED','OUTCOME_UNKNOWN')"
        )["n"], 3)
        self.assertEqual(self.count(self.a), 1)
        self.assertEqual(self.count(b), 2)
        self.r.store.finish_action(b1, "CANCELLED", {
            "role": "SOURCE_COPY", "action_duration_s": 0.0
        })
        self.assertEqual(self.count(self.a), 1)
        self.assertEqual(self.count(b), 1)
        c = self.r.store.new_session()
        self.assertEqual(self.count(c), 0)
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.assertEqual(self.count(self.a), 1)
        self.assertEqual(self.count(b), 1)
        self.assertEqual(self.count(c), 0)
        self.assertEqual(self.r.store.integrity(True), [])

    def test_single_session_unfinished_action_baseline(self):
        self.assertEqual(self.count(self.a), 0)
        aid = self.start(self.a, "One local action")
        self.assertEqual(self.count(self.a), 1)
        self.r.store.finish_action(aid, "ERROR", {
            "role": "SOURCE_COPY", "action_duration_s": 0.0
        })
        self.assertEqual(self.count(self.a), 0)


if __name__ == "__main__":
    unittest.main()
