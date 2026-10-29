"""S7 must page >64 interleaved FINAL events without losing original user chronology.

Real Store-only lineage; no model, training, age promotion or Redmi proof.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13 import sleep_offline as S


class UserCursorOverflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.session = self.r.session

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def events(self, n):
        return [self.r.store.event(
            self.session, "Source-valid user event %03d, value %03d." % (i, i))
            for i in range(n)]

    def answer(self, event, i):
        self.r.store.message(self.session, event["event_id"], "assistant",
                             "Source-bound FINAL answer %03d." % i,
                             status="FINAL", metadata={"direct_source_copy": True})

    def entries(self):
        state, _ = self.r.store.state(S.KEY)
        return state["sessions"][self.session]["entries"]

    def test_130_users_then_reverse_answers_recover_64_64_2_across_restart(self):
        events = self.events(130)
        for i in reversed(range(130)):
            self.answer(events[i], i)
        self.assertEqual(S.digest(self.r.store)["turns"], 64)
        self.assertEqual([x["event_id"] for x in self.entries()],
                         [e["event_id"] for e in events[:64]])
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.assertEqual(S.digest(self.r.store)["turns"], 64)
        self.assertEqual(S.digest(self.r.store)["turns"], 2)
        self.assertEqual(S.digest(self.r.store)["turns"], 0)
        self.assertEqual([x["event_id"] for x in self.entries()],
                         [e["event_id"] for e in events[-S.ENTRIES_MAX:]])
        # Live context must still revalidate all 96 exact sources, even
        # though the latest 194 message rows contain only 64 user rows.
        self.assertEqual(S.view(self.r.store, self.session, cap=100000)["entries"],
                         S.ENTRIES_MAX)

    def test_pending_first_user_blocks_then_late_completion_recovers(self):
        events = self.events(65)
        for i in reversed(range(1, 65)):
            self.answer(events[i], i)
        self.assertEqual(S.digest(self.r.store)["turns"], 0)
        self.answer(events[0], 0)
        self.assertEqual(S.digest(self.r.store)["turns"], 64)
        self.assertEqual(S.digest(self.r.store)["turns"], 1)
        self.assertEqual(S.digest(self.r.store)["turns"], 0)
        self.assertEqual([x["event_id"] for x in self.entries()],
                         [e["event_id"] for e in events])

    def test_malformed_one_cached_entry_does_not_hide_other_exact_sources(self):
        events = self.events(3)
        for i, event in enumerate(events):
            self.answer(event, i)
        self.assertEqual(S.digest(self.r.store)["turns"], 3)
        state, version = self.r.store.state(S.KEY)
        state["sessions"][self.session]["entries"][0] = None
        self.r.store.set_state(S.KEY, state, expected=version)
        self.assertEqual(S.view(self.r.store, self.session, cap=100000)["entries"], 2)

    def test_deleted_source_stays_excluded_without_blocking_backlog(self):
        events = self.events(65)
        for i in reversed(range(65)):
            self.answer(events[i], i)
        with self.r.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",
                      (events[5]["source_ref"]["source_id"],))
        self.assertEqual(S.digest(self.r.store)["turns"], 63)
        self.assertEqual(S.digest(self.r.store)["turns"], 1)
        self.assertEqual(S.digest(self.r.store)["turns"], 0)
        ids = [x["event_id"] for x in self.entries()]
        self.assertNotIn(events[5]["event_id"], ids)
        self.assertEqual(len(ids), 64)
        self.assertEqual(S.view(self.r.store, self.session, cap=100000)["entries"], 64)


if __name__ == "__main__":
    unittest.main()
