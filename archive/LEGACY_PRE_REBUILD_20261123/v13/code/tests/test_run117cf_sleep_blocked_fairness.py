"""Run117CF: pending DRAFT in eight sessions must not starve a ready ninth.

Real SQLite Store and authoritative USER SourceRefs; software-only regression.
"""
from pathlib import Path
import tempfile
import unittest

from v13.config import initialize
from v13.store import Store
from v13 import sleep_offline as S


class SleepBlockedFairness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        initialize(self.home)
        self.s = Store(self.home)

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def turn(self, session, marker, status="FINAL"):
        e = self.s.event(session, "BLOCKED_SOURCE_" + marker)
        mid = self.s.message(session, e["event_id"], "assistant",
                             "BLOCKED_ANSWER_" + marker, status,
                             {"direct_source_copy": True})
        return mid

    def test_eight_unfinished_sessions_cannot_starve_ready_ninth(self):
        drafts = []
        blocked = []
        for i in range(8):
            sid = self.s.new_session()
            blocked.append(sid)
            drafts.append(self.turn(sid, f"{i}_DRAFT", "DRAFT"))
            self.turn(sid, f"{i}_FINAL")
        ready = self.s.new_session()
        self.turn(ready, "READY")
        first = S.digest(self.s)
        self.assertEqual(first["turns"], 1)
        self.assertEqual(first["blocked_sessions"], 8)
        self.assertEqual(first["deferred_sessions"], 8)
        state = self.s.state(S.KEY, None)[0]
        self.assertEqual([e["user"] for e in state["sessions"][ready]["entries"]],
                         ["BLOCKED_SOURCE_READY"])
        for sid in blocked:
            self.assertNotIn(sid, state["sessions"])

        self.s.finish_message(drafts[0], "FINAL", {"direct_source_copy": True})
        second = S.digest(self.s)
        self.assertEqual(second["turns"], 2)
        self.assertEqual(second["blocked_sessions"], 7)
        self.assertEqual([e["user"] for e in self.s.state(S.KEY, None)[0]["sessions"][blocked[0]]["entries"]],
                         ["BLOCKED_SOURCE_0_DRAFT", "BLOCKED_SOURCE_0_FINAL"])

    def test_all_blocked_is_deferred_until_source_final(self):
        sid = self.s.new_session()
        draft = self.turn(sid, "WAIT", "DRAFT")
        self.turn(sid, "LATER")
        first = S.digest(self.s)
        self.assertEqual(first["turns"], 0)
        self.assertEqual(first["sessions"], 0)
        self.assertEqual(first["blocked_sessions"], 1)
        self.assertEqual(first["deferred_sessions"], 1)
        self.s.finish_message(draft, "FINAL", {"direct_source_copy": True})
        second = S.digest(self.s)
        self.assertEqual(second["turns"], 2)
        self.assertEqual(second["blocked_sessions"], 0)


if __name__ == "__main__":
    unittest.main()
