"""G13 prospective fail-closed dispatch-clock regression (software-only)."""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.scheduler import EventScheduler


class Clock:
    def __init__(self, value=1000.):
        self.value = value

    def __call__(self):
        return self.value


class DispatchClockBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.clock = Clock()
        self.scheduler = EventScheduler(
            self.runtime.store, self.runtime.cfg, self.clock,
            key="G13_DISPATCH_CLOCK_CANDIDATE_TEST")

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def test_invalid_clock_does_not_dispatch_expire_or_mutate(self):
        s = self.scheduler
        first = s.post("TIMER", origin="USER", due=1010., ttl=20., action="sleep_c")
        second = s.post("IDLE", due=1020., ttl=30., action="notice")
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        before_report = s.report()
        before_pending = s.pending()
        before_telemetry = self.runtime.store.rows(
            "SELECT id FROM telemetry WHERE kind='scheduler_dispatch'")
        for bad in (float("nan"), float("inf"), -float("inf"), None, "not-a-clock"):
            with self.subTest(clock=repr(bad)):
                self.clock.value = bad
                with self.assertRaisesRegex(ValueError, "dispatch clock"):
                    s.next()
                self.assertEqual(s.report(), before_report)
                self.assertEqual(s.pending(), before_pending)
                self.assertEqual(
                    self.runtime.store.rows(
                        "SELECT id FROM telemetry WHERE kind='scheduler_dispatch'"),
                    before_telemetry)

        self.clock.value = 1011.
        dispatched = s.next()
        self.assertEqual(dispatched["id"], first)
        self.assertEqual(dispatched["attempts"], 1)
        self.assertEqual(s.complete(first, "DONE"), "DONE")
        self.clock.value = 1060.
        self.assertIsNone(s.next())
        self.assertEqual(s.report()["counters"]["expired"], 1)
        self.assertEqual(s.report()["counters"]["dispatched"], 1)

    def test_finite_clock_keeps_priority_and_retry_semantics(self):
        s = self.scheduler
        self.clock.value = 1000.
        low = s.post("IDLE", action="notice")
        high = s.post("RESOURCE_CHANGE", action="notice")
        self.assertEqual(s.next()["id"], high)
        self.assertEqual(s.complete(high, "DONE"), "DONE")
        self.assertEqual(s.next()["id"], low)
        self.assertEqual(s.complete(low, "RETRY"), "PENDING")
        self.assertEqual(s.next()["attempts"], 2)


if __name__ == "__main__":
    unittest.main()
