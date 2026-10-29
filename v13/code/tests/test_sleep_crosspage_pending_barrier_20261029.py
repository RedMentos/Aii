"""S7 cannot cross an unresolved user hidden beyond its 64-user scan page.

Real Store-only, source-valid FINAL fixtures. No model, training, Redmi or gate promotion.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13 import sleep_offline as S


class CrossPagePendingBarrier(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.session = self.r.session

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _events(self, n):
        return [self.r.store.event(self.session, "Source-valid user %03d." % i)
                for i in range(n)]

    def _answer(self, event, i):
        self.r.store.message(self.session, event["event_id"], "assistant",
                             "Source-bound FINAL answer %03d." % i,
                             status="FINAL", metadata={"direct_source_copy": True})

    def _ids(self):
        state, _ = self.r.store.state(S.KEY)
        return [e["event_id"] for e in state["sessions"][self.session]["entries"]]

    def test_pending_65th_user_blocks_first_64_then_restarts_and_recovers(self):
        events = self._events(65)
        for i in reversed(range(64)):
            self._answer(events[i], i)
        self.assertEqual(S.digest(self.r.store)["turns"], 0)
        self._answer(events[64], 64)
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.assertEqual(S.digest(self.r.store)["turns"], 64)
        self.assertEqual(S.digest(self.r.store)["turns"], 1)
        self.assertEqual(self._ids(), [e["event_id"] for e in events])

    def test_pending_70th_user_blocks_even_if_65th_is_final(self):
        events = self._events(70)
        for i in reversed(range(69)):
            self._answer(events[i], i)
        self.assertEqual(S.digest(self.r.store)["turns"], 0)
        self._answer(events[69], 69)
        self.assertEqual(S.digest(self.r.store)["turns"], 64)
        self.assertEqual(S.digest(self.r.store)["turns"], 6)
        self.assertEqual(self._ids(), [e["event_id"] for e in events])

    def test_fully_settled_reverse_130_still_pages_64_64_2(self):
        events = self._events(130)
        for i in reversed(range(130)):
            self._answer(events[i], i)
        self.assertEqual(S.digest(self.r.store)["turns"], 64)
        self.assertEqual(S.digest(self.r.store)["turns"], 64)
        self.assertEqual(S.digest(self.r.store)["turns"], 2)
        self.assertEqual(S.digest(self.r.store)["turns"], 0)
        self.assertEqual(self._ids(), [e["event_id"] for e in events[-S.ENTRIES_MAX:]])


if __name__ == "__main__":
    unittest.main()
