"""S7 per-run bounded scheduling must not starve older pending sessions."""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13 import sleep_offline as S


class DigestSessionFairness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.sessions = [self.r.store.new_session("digest-%02d" % i) for i in range(10)]

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def turn(self, session, n):
        e = self.r.store.event(session, "Source-valid session %s, turn %d." % (session, n))
        self.r.store.message(
            session, e["event_id"], "assistant", "Source-bound answer %d." % n,
            status="FINAL", metadata={"direct_source_copy": True})
        return e

    def test_ten_sessions_eventually_digest_in_eight_plus_two_batches(self):
        for i, session in enumerate(self.sessions):
            self.turn(session, i)
        self.assertEqual(S.digest(self.r.store)["turns"], 8)
        self.assertEqual(S.digest(self.r.store)["turns"], 2)
        self.assertEqual(S.digest(self.r.store)["turns"], 0)
        st, _ = self.r.store.state(S.KEY)
        self.assertEqual(set(st["sessions"]), set(self.sessions))
        self.assertTrue(all(len(st["sessions"][sid]["entries"]) == 1
                            for sid in self.sessions))

    def test_newer_activity_does_not_permanently_starve_oldest_session(self):
        for i, session in enumerate(self.sessions[:9]):
            self.turn(session, i)
        self.assertEqual(S.digest(self.r.store)["turns"], 8)
        # The newest already-digested session receives another FINAL turn.
        self.turn(self.sessions[8], 100)
        self.assertEqual(S.digest(self.r.store)["turns"], 2)
        self.assertEqual(S.digest(self.r.store)["turns"], 0)
        st, _ = self.r.store.state(S.KEY)
        self.assertEqual(len(st["sessions"][self.sessions[0]]["entries"]), 1)
        self.assertEqual(len(st["sessions"][self.sessions[8]]["entries"]), 2)

    def test_tombstoned_old_session_is_scanned_but_never_exposed(self):
        events = [self.turn(sid, i) for i, sid in enumerate(self.sessions[:9])]
        with self.r.store.tx() as cur:
            cur.execute("UPDATE sources SET deleted=1 WHERE id=?",
                        (events[0]["source_ref"]["source_id"],))
        # Fair scheduling may scan the revoked oldest session first. The
        # invariant is eight valid digests in total, never nine.
        total = S.digest(self.r.store)["turns"] + S.digest(self.r.store)["turns"]
        self.assertEqual(total, 8)
        self.assertEqual(S.digest(self.r.store)["turns"], 0)
        st, _ = self.r.store.state(S.KEY)
        self.assertIn(self.sessions[0], st["sessions"])
        self.assertEqual(st["sessions"][self.sessions[0]]["entries"], [])
        self.assertEqual(S.view(self.r.store, self.sessions[0], cap=10000)["entries"], 0)


    def test_eight_stalled_sessions_cannot_starve_a_ninth_valid_session(self):
        # Each stalled session has an unfinished older event and a later
        # FINAL event. S7 must not repeatedly spend all eight slots on them.
        for i, session in enumerate(self.sessions[:8]):
            self.r.store.event(session, "Unfinished older request %d." % i)
            self.turn(session, i)
        valid = self.turn(self.sessions[8], 900)
        self.assertEqual(S.digest(self.r.store)["turns"], 0)
        self.assertEqual(S.digest(self.r.store)["turns"], 1)
        st, _ = self.r.store.state(S.KEY)
        self.assertEqual(st["sessions"][self.sessions[8]]["entries"][0]["event_id"],
                         valid["event_id"])


if __name__ == "__main__":
    unittest.main()
