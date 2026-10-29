"""S7 must digest source-valid interleaved FINAL events without skipping unfinished predecessors."""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13 import sleep_offline as S


class InterleavedFinal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.s = self.r.store
        self.session = self.r.session

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self, name):
        return self.s.event(self.session, "Source-valid request: " + name)

    def answer(self, e, name, status="FINAL"):
        return self.s.message(self.session, e["event_id"], "assistant",
                              "Source-bound answer: " + name, status=status,
                              metadata={"direct_source_copy": True})

    def entries(self):
        state, _ = self.s.state(S.KEY)
        return state["sessions"][self.session]["entries"]

    def test_reversed_assistant_completion_keeps_original_user_order(self):
        first, second = self.event("first"), self.event("second")
        self.answer(second, "second")
        self.answer(first, "first")
        self.assertEqual(S.digest(self.s)["turns"], 2)
        self.assertEqual([x["event_id"] for x in self.entries()],
                         [first["event_id"], second["event_id"]])
        self.assertEqual(S.digest(self.s)["turns"], 0)

    def test_incomplete_predecessor_never_skipped_then_recovers(self):
        first, second = self.event("first"), self.event("second")
        self.answer(second, "second")
        self.assertEqual(S.digest(self.s)["turns"], 0)
        self.answer(first, "first")
        self.assertEqual(S.digest(self.s)["turns"], 2)
        self.assertEqual([x["event_id"] for x in self.entries()],
                         [first["event_id"], second["event_id"]])

    def test_cancelled_predecessor_does_not_become_a_digest_fact(self):
        first, second = self.event("first"), self.event("second")
        self.answer(second, "second")
        self.answer(first, "cancelled", status="CANCELLED")
        self.assertEqual(S.digest(self.s)["turns"], 1)
        self.assertEqual([x["event_id"] for x in self.entries()],
                         [second["event_id"]])

    def test_duplicate_assistant_blocks_highwater_not_skip_corrupt_event(self):
        first = self.event("first")
        self.answer(first, "first")
        self.answer(first, "duplicate")
        second = self.event("second")
        self.answer(second, "second")
        self.assertEqual(S.digest(self.s)["turns"], 0)
        self.assertEqual(self.entries(), [])


    def test_late_earlier_answer_must_not_skip_interleaved_pending_user(self):
        first, second = self.event("first"), self.event("second")
        self.answer(first, "first")
        # The first answer is after the second user's row. Advancing the
        # assistant high-water would irreversibly skip the second source.
        self.assertEqual(S.digest(self.s)["turns"], 0)
        self.answer(second, "second")
        self.assertEqual(S.digest(self.s)["turns"], 2)
        self.assertEqual([x["event_id"] for x in self.entries()],
                         [first["event_id"], second["event_id"]])


if __name__ == "__main__":
    unittest.main()
