"""Run18 test-first: F9 Sleep explicit replay batch cannot bypass policy budget."""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.sleep import SCHEDULE_KEY


class SleepBatchBudget(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        for i in range(5):
            e = self.r.store.event(self.r.session, "Run18 correction " + str(i))["event_id"]
            self.r.memory.feedback(e, "fact", "Run18 verified value " + str(i),
                                   key="Run18 correction " + str(i))
        self.c = self.r.sleep.cycle

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _a_packets(self):
        return self.r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='ReplayItem' "
            "AND json_extract(payload,'$.stage')='SLEEP_A'"
        )["n"]

    def test_invalid_explicit_batch_fails_before_any_durable_side_effect(self):
        invalid = (-1, 0, True, 1.5, "2", 65, 10**9)
        for value in invalid:
            with self.subTest(value=repr(value)):
                before = self.r.store.state(SCHEDULE_KEY, None)
                packets = self._a_packets()
                with self.assertRaises(ValueError):
                    self.c.run("a", origin="USER", batch=value)
                self.assertEqual(self.r.store.state(SCHEDULE_KEY, None), before)
                self.assertEqual(self._a_packets(), packets)

    def test_exact_positive_batch_is_hard_selection_ceiling(self):
        one = self.c.run("a", origin="USER", batch=1)["phases"][0]
        self.assertEqual(one["selected"], 1)
        two = self.c.run("a", origin="USER", batch=2)["phases"][0]
        self.assertEqual(two["selected"], 2)
        rest = self.c.run("a", origin="USER", batch=None)["phases"][0]
        self.assertEqual(rest["selected"], 2)
        self.assertEqual(self._a_packets(), 5)
        self.assertEqual(self.r.store.one("SELECT COUNT(*) AS n FROM replay")["n"], 5)

    def test_wake_ceiling_and_unrelated_phases_reject_invalid_batch(self):
        for mode, value in (("wake", 9), ("wake", -1), ("b", -1), ("c", "3")):
            with self.subTest(mode=mode, value=value):
                before = self.r.store.state(SCHEDULE_KEY, None)
                with self.assertRaises(ValueError):
                    self.c.run(mode, origin="USER", batch=value)
                self.assertEqual(self.r.store.state(SCHEDULE_KEY, None), before)
        allowed = self.c.run("wake", origin="USER", batch=8)
        self.assertLessEqual(allowed["phases"][0]["selected"], 8)


if __name__ == "__main__":
    unittest.main()
