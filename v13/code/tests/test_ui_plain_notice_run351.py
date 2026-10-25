"""Run351 RED-first: plain Termux UI must flush notices after typing ends.

Fake operator and store; real UI render thread, no native/model/phone action.
"""
import contextlib
import io
import threading
import time
import unittest
from unittest.mock import patch

from v13 import ui as U


class FakeStore:
    def history(self, session, limit):
        return []


class FakeRuntime:
    def __init__(self):
        self.stop = threading.Event()
        self.store = FakeStore()
        self.session = "synthetic-chat"
        self.notify = None

    def cancel(self):
        pass


class FakeOperator:
    def __init__(self, runtime):
        self.runtime = runtime

    def run(self, line):
        return ""


class PlainNoticeRun351(unittest.TestCase):
    def simulate(self, notices, initially_typing=True):
        r = FakeRuntime()
        state = {"typing": initially_typing}
        output = io.StringIO()
        before = []

        def fake_read(prompt):
            for notice in notices:
                r.notify(notice)
            # Allow at least one render tick while the operator is typing.
            time.sleep(.16)
            before.append(output.getvalue())
            state["typing"] = False
            until = time.monotonic() + .55
            while time.monotonic() < until:
                if all(("[V13] " + x) in output.getvalue() for x in notices):
                    break
                time.sleep(.01)
            raise EOFError

        with patch.object(U, "Operator", FakeOperator), \
             patch.object(U, "watch_buttons", lambda r: None), \
             patch.object(U, "typing", lambda: state["typing"]), \
             patch.object(U, "read_block", side_effect=fake_read), \
             contextlib.redirect_stdout(output):
            U.plain(r)
        return before[0], output.getvalue()

    def test_held_notice_flushes_without_second_notification(self):
        before, after = self.simulate(["queued while typing"])
        self.assertNotIn("[V13] queued while typing", before)
        self.assertIn("[V13] queued while typing", after)

    def test_multiple_held_notices_flush_once_in_fifo_order(self):
        before, after = self.simulate(["first pending", "second pending"])
        self.assertNotIn("[V13] first pending", before)
        self.assertEqual(after.count("[V13] first pending"), 1)
        self.assertEqual(after.count("[V13] second pending"), 1)
        self.assertLess(after.index("[V13] first pending"),
                        after.index("[V13] second pending"))

    def test_notice_without_active_typing_is_immediate(self):
        before, after = self.simulate(["immediate notice"], initially_typing=False)
        self.assertIn("[V13] immediate notice", before)
        self.assertEqual(after.count("[V13] immediate notice"), 1)


if __name__ == "__main__":
    unittest.main()
