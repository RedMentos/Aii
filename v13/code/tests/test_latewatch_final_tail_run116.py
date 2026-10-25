"""Run116: finished C3 numeric tail must not be treated as an unfinished token."""
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from v13 import latewatch as lw

SOURCE = "What is 46 plus 62?"
OFFER = {
    "role": "B1_DETAIL",
    "packet_id": "source-bound-late-offer",
    "offer": {"summary": "46 + 62 = 108", "needs_reentry": False, "quotes": []},
}
WRONG = "After checking the arithmetic carefully, the answer is 100"
RIGHT = "After checking the arithmetic carefully, the answer is 108"


class LateWatchFinalTailRun116(unittest.TestCase):
    def test_partial_tail_is_still_ignored_but_completed_tail_is_checked(self):
        self.assertIsNone(lw.disagreement(OFFER, WRONG, SOURCE))
        self.assertEqual(lw.disagreement(OFFER, WRONG, SOURCE, final=True), "RESULT_CONFLICT")
        self.assertIsNone(lw.disagreement(OFFER, RIGHT, SOURCE, final=True))
        self.assertIsNone(lw.disagreement(OFFER, "After checking carefully, 46 and 62", SOURCE, final=True))

    def test_finish_records_completed_numeric_conflict_without_active_cut(self):
        stored = SimpleNamespace(read_source=lambda ref: SOURCE, log=mock.Mock())
        r = SimpleNamespace(store=stored)
        event = {"event_id": "e", "source_ref": "human-source"}
        w = lw.Watcher(r, event, {}, "shadow", role="B1_DETAIL", status="RUNNING")
        w.thread = object()
        w.offer = OFFER
        w.done.set()
        controller = SimpleNamespace(late_offer=mock.Mock())
        with mock.patch.object(lw, "_record") as record, mock.patch(
            "v13.selfmodel.controller", return_value=controller
        ):
            result = w.finish(None, [], WRONG, time.monotonic() + 1, "m")
        self.assertEqual(result, "")
        self.assertEqual(w.status, "AFTER_OUTPUT")
        self.assertEqual(w.info["reason"], "RESULT_CONFLICT")
        controller.late_offer.assert_called_once_with("e", OFFER, WRONG)
        record.assert_called_once()

    def test_finish_completed_correct_tail_is_not_a_conflict(self):
        stored = SimpleNamespace(read_source=lambda ref: SOURCE, log=mock.Mock())
        r = SimpleNamespace(store=stored)
        w = lw.Watcher(r, {"event_id": "e", "source_ref": "human-source"}, {}, "shadow", role="B1_DETAIL", status="RUNNING")
        w.thread = object()
        w.offer = OFFER
        w.done.set()
        with mock.patch.object(lw, "_record"), mock.patch("v13.selfmodel.controller"):
            w.finish(None, [], RIGHT, time.monotonic() + 1, "m")
        self.assertEqual(w.status, "AFTER_OUTPUT")
        self.assertNotIn("reason", w.info)


if __name__ == "__main__":
    unittest.main()
