"""G13 durable timer boundary: reject invalid time before any queue mutation."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13.scheduler import EventScheduler


class Clock:
    def __init__(self, t=1000.):
        self.t = t
    def __call__(self):
        return self.t


class SchedulerFiniteBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.clock = Clock()
        self.scheduler = EventScheduler(
            self.r.store, self.r.cfg, self.clock,
            key="G13_FINITE_BOUNDARY_TEST")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_invalid_due_ttl_and_clock_do_not_mutate_queue(self):
        s = self.scheduler
        before = s.report()
        for field, value in (
            ("due", float("nan")), ("due", float("inf")),
            ("due", -float("inf")), ("ttl", float("nan")),
            ("ttl", float("inf")), ("ttl", -float("inf")),
            ("ttl", -1.),
        ):
            with self.subTest(field=field, value=repr(value)):
                with self.assertRaises(ValueError):
                    s.post("TIMER", origin="USER", action="sleep_c",
                           **{field: value})
                self.assertEqual(s.report(), before)
        self.clock.t = float("nan")
        with self.assertRaisesRegex(ValueError, "clock"):
            s.post("TIMER", origin="USER", action="sleep_c")
        self.clock.t = 1e308
        with self.assertRaisesRegex(ValueError, "TTL"):
            s.post("TIMER", origin="USER", action="sleep_c", ttl=1e308)
        self.clock.t = 1000.
        self.assertEqual(s.report(), before)

    def test_invalid_high_priority_timer_cannot_evict_pending(self):
        s = self.scheduler
        with patch("v13.scheduler.MAX_PENDING", 1):
            low = s.post("IDLE", action="sleep_a")
            self.assertIsNotNone(low)
            before = s.pending()
            with self.assertRaisesRegex(ValueError, "due"):
                s.post("RESOURCE_CHANGE", due=float("nan"))
            self.assertEqual(s.pending(), before)
            self.assertEqual(s.report()["counters"].get("dropped_capacity", 0), 0)

    def test_valid_finite_user_timer_retains_due_and_expiry(self):
        s = self.scheduler
        timer = s.post("TIMER", origin="USER", action="sleep_c",
                       due=1060., ttl=120.)
        self.assertIsNotNone(timer)
        pending = s.pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["due"], 1060.)
        self.assertEqual(pending[0]["expires"], 1120.)
        self.assertEqual(pending[0]["origin"], "USER")
        self.assertEqual(pending[0]["action"], "sleep_c")


if __name__ == "__main__":
    unittest.main()
