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


    def test_concurrent_new_notice_cannot_overtake_held_fifo_during_render(self):
        r = FakeRuntime()
        state = {"typing": True}
        output = io.StringIO()
        entered = threading.Event()
        release = threading.Event()
        original_safe = U.safe_text

        def slow_safe(text):
            if text == "first delayed":
                entered.set()
                release.wait(.8)
            return original_safe(text)

        def fake_read(prompt):
            r.notify("first delayed")
            state["typing"] = False
            self.assertTrue(entered.wait(.6), "render never attempted held notice")
            thread = threading.Thread(target=lambda: r.notify("second immediate"))
            thread.start()
            try:
                time.sleep(.05)  # let the competing worker reach notify
            finally:
                release.set()
                thread.join(.8)
            self.assertFalse(thread.is_alive(), "concurrent notifier blocked")
            until = time.monotonic() + .4
            while time.monotonic() < until and "[V13] second immediate" not in output.getvalue():
                time.sleep(.01)
            raise EOFError

        with patch.object(U, "Operator", FakeOperator), \
             patch.object(U, "watch_buttons", lambda r: None), \
             patch.object(U, "typing", lambda: state["typing"]), \
             patch.object(U, "safe_text", side_effect=slow_safe), \
             patch.object(U, "read_block", side_effect=fake_read), \
             contextlib.redirect_stdout(output):
            U.plain(r)
        result = output.getvalue()
        self.assertEqual(result.count("[V13] first delayed"), 1)
        self.assertEqual(result.count("[V13] second immediate"), 1)
        self.assertLess(result.index("[V13] first delayed"),
                        result.index("[V13] second immediate"))


if __name__ == "__main__":
    unittest.main()
