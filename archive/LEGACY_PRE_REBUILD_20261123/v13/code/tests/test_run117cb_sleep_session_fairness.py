"""Run117CB: Sleep's eight-session budget must not starve older sessions.

Actual persisted Store and source validation; software only, no native model.
"""
from pathlib import Path
import tempfile
import unittest

from v13.config import initialize
from v13.store import Store
from v13 import sleep_offline as S


class SleepSessionFairness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        initialize(self.home)
        self.s = Store(self.home)

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def turn(self, session, marker):
        e = self.s.event(session, f"FAIR_SOURCE_{marker}")
        self.s.message(session, e["event_id"], "assistant",
                       f"FAIR_ANSWER_{marker}", "FINAL",
                       {"direct_source_copy": True})
        return e

    def state(self):
        return self.s.state(S.KEY, None)[0]

    def test_ten_sessions_all_eventually_digested_in_two_bounded_cycles(self):
        sessions = [self.s.new_session() for _ in range(10)]
        for i, session in enumerate(sessions):
            self.turn(session, f"{i:02d}")
        first = S.digest(self.s)
        self.assertEqual((first["sessions"], first["turns"], first["deferred_sessions"]),
                         (8, 8, 2))
        self.assertEqual(len(self.state()["sessions"]), 8)
        second = S.digest(self.s)
        self.assertEqual((second["sessions"], second["turns"], second["deferred_sessions"]),
                         (2, 2, 0))
        self.assertEqual(len(self.state()["sessions"]), 10)
        self.assertEqual(S.digest(self.s)["turns"], 0)
        for i, session in enumerate(sessions):
            d = self.state()["sessions"][session]
            self.assertEqual([x["user"] for x in d["entries"]],
                             [f"FAIR_SOURCE_{i:02d}"])

    def test_busy_processed_sessions_cannot_starve_unseen_older_sessions(self):
        sessions = [self.s.new_session() for _ in range(12)]
        for i, session in enumerate(sessions):
            self.turn(session, f"{i:02d}")
        first = S.digest(self.s)
        self.assertEqual(first["sessions"], 8)
        processed = set(self.state()["sessions"])
        unseen = set(sessions) - processed
        self.assertEqual(len(unseen), 4)
        # New activity in previously processed sessions must not displace
        # the four still-unprocessed sessions on the next bounded cycle.
        hot = list(processed)[:4]
        for i, session in enumerate(hot):
            self.turn(session, f"HOT_{i:02d}")
        second = S.digest(self.s)
        self.assertEqual(second["sessions"], 8)
        self.assertEqual(second["deferred_sessions"], 0)
        self.assertTrue(unseen.issubset(self.state()["sessions"]))
        self.assertEqual(len(self.state()["sessions"]), 12)
        for session in hot:
            self.assertEqual(len(self.state()["sessions"][session]["entries"]), 2)

    def test_restart_keeps_fair_cursors_and_revoked_source_excluded(self):
        sessions = [self.s.new_session() for _ in range(10)]
        refs = [self.turn(session, f"{i:02d}") for i, session in enumerate(sessions)]
        with self.s.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",
                      (refs[0]["source_ref"]["source_id"],))
        first = S.digest(self.s)
        self.assertEqual(first["sessions"], 8)
        self.s.close()
        self.s = Store(self.home)
        second = S.digest(self.s)
        self.assertEqual(second["sessions"], 2)
        self.assertEqual(len(self.state()["sessions"]), 10)
        self.assertEqual(S.digest(self.s)["turns"], 0)
        self.assertEqual(self.state()["sessions"][sessions[0]]["entries"], [])
        for session in sessions:
            self.assertNotIn("FAIR_SOURCE_00",
                             "\n".join(S.context_items(self.s, session, cap=20000)))


if __name__ == "__main__":
    unittest.main()
