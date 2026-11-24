"""G13 burnout budget must not reset under a rolled-back scheduler clock."""
import tempfile
import unittest
from pathlib import Path

from v13.inputs import set_burnout
from v13.runtime import Runtime
from v13.scheduler import DISPATCH_LEDGER_MAX, EventScheduler


class Clock:
    def __init__(self, value=1000.):
        self.value = value

    def __call__(self):
        return self.value


class BurnoutClockRollbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.clock = Clock()
        self.scheduler = EventScheduler(
            self.runtime.store, self.runtime.cfg, self.clock,
            key="G13_BURNOUT_CLOCK_ROLLBACK_TEST")
        set_burnout(self.runtime.store, 1)

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def accepted(self, at):
        event = self.runtime.store.event(self.runtime.session, "Clock-boundary user turn")
        with self.runtime.store.tx() as tx:
            tx.execute(
                "INSERT INTO accepted_turns(event_id,bytes,accepted_at,state) "
                "VALUES (?,?,?,?)",
                (event["event_id"], 1, at, "DONE"))

    def test_future_accepted_turn_blocks_background_until_clock_catches_up(self):
        s = self.scheduler
        self.accepted(1010.)
        wake = s.post("IDLE", action="sleep_a", due=1000.)
        before = s.pending()
        self.assertEqual(s.background_since_input(), DISPATCH_LEDGER_MAX)
        self.assertIsNone(s.next())
        self.assertEqual(s.pending(), before)
        self.assertEqual(s.report()["counters"].get("dispatched", 0), 0)

        # User input must not be starved by background-budget containment.
        user = s.post("USER_INPUT", origin="USER")
        self.assertEqual(s.next(idle=False)["id"], user)
        self.assertEqual(s.complete(user, "DONE"), "DONE")

        self.clock.value = 1011.
        self.assertEqual(s.background_since_input(), 0)
        self.assertEqual(s.next()["id"], wake)
        self.assertEqual(s.background_since_input(), 1)
        self.assertEqual(s.complete(wake, "DONE"), "DONE")
        s.post("IDLE", action="sleep_a")
        self.assertIsNone(s.next())  # budget=1, no unlimited background wake

    def test_malformed_accepted_time_conservatively_exhausts_budget(self):
        s = self.scheduler
        self.accepted("not-a-timestamp")
        s.post("IDLE", action="sleep_a")
        self.assertEqual(s.background_since_input(), DISPATCH_LEDGER_MAX)
        self.assertIsNone(s.next())
        self.assertEqual(s.report()["counters"].get("dispatched", 0), 0)

    def test_invalid_budget_clock_rejected_without_mutation(self):
        s = self.scheduler
        self.accepted(1000.)
        s.post("IDLE", action="sleep_a")
        before = s.report()
        for invalid in (float("nan"), float("inf"), -float("inf"), None):
            with self.subTest(value=repr(invalid)):
                self.clock.value = invalid
                with self.assertRaisesRegex(ValueError, "budget clock"):
                    s.background_since_input()
                self.assertEqual(s.report(), before)


if __name__ == "__main__":
    unittest.main()
