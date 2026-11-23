"""Sleep/Dream user timer: invalid delay must not become an immediate job."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13.operator import Operator


class SleepFiniteDelayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_invalid_direct_delays_never_publish_or_tick(self):
        sl = self.r.sleep
        with patch.object(sl.scheduler, "post",
                          side_effect=AssertionError("unexpected timer")), \
             patch.object(sl, "tick",
                          side_effect=AssertionError("unexpected wake")):
            for delay in (float("nan"), float("inf"), -float("inf"),
                          -1., -0.1, "nan", "not-a-delay"):
                with self.subTest(delay=repr(delay)), self.assertRaises(
                        (ValueError, OverflowError)):
                    sl.request("c", delay)
            with patch.object(sl, "clock", return_value=1e308):
                with self.assertRaisesRegex(ValueError, "due time"):
                    sl.request("c", 1e308)

    def test_invalid_operator_delay_does_not_enqueue_sleep(self):
        before = self.r.sleep.scheduler.report()
        with patch.object(self.r.sleep.scheduler, "post",
                          side_effect=AssertionError("unexpected timer")), \
             patch.object(self.r.sleep, "tick",
                          side_effect=AssertionError("unexpected wake")):
            for text in (":sleep in nan", ":sleep in inf",
                         ":sleep in -inf", ":sleep in -1"):
                with self.subTest(text=text), self.assertRaises(ValueError):
                    self.op.run(text)
        self.assertEqual(self.r.sleep.scheduler.report(), before)
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")

    def test_valid_positive_delay_keeps_user_timer_and_existing_tick(self):
        sl = self.r.sleep
        with patch.object(sl, "clock", return_value=1000.), \
             patch.object(sl.scheduler, "post", return_value="timer-id") as post, \
             patch.object(sl, "tick") as tick:
            self.assertEqual(sl.request("c", 60.), "timer-id")
        post.assert_called_once_with(
            "TIMER", origin="USER", due=1060., action="sleep_c")
        tick.assert_called_once_with(force=True)


if __name__ == "__main__":
    unittest.main()
