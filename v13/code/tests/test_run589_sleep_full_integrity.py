"""Run589: partial or interrupted full Sleep cannot claim a complete night."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from v13.runtime import Runtime
from v13.agi import after_sleep


class Run589SleepFullIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.cy = self.r.sleep.cycle

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def last_full(self):
        return self.cy.queue.load()[0]["last_full"]

    def test_full_under_pressure_runs_only_c_but_does_not_complete_night(self):
        before = self.last_full()
        with mock.patch.object(self.cy, "sleep_a") as a, \
             mock.patch.object(self.cy, "sleep_b") as b, \
             mock.patch.object(self.cy, "sleep_c", return_value={"phase":"SLEEP_C","status":"DONE"}) as c:
            rep = self.cy.run("full", origin="USER", resource=lambda: "PRESSURE")
        self.assertEqual([p["phase"] for p in rep["phases"]], ["SLEEP_C"])
        self.assertEqual(rep["status"], "SKIPPED_RESOURCE_YELLOW")
        self.assertEqual(self.last_full(), before)
        a.assert_not_called();b.assert_not_called();c.assert_called_once()
        self.assertIsNone(after_sleep(self.r.sleep, {"origin":"USER"}, rep))

    def test_interrupted_a_stops_offline_b_c_and_does_not_advance_full_clock(self):
        before = self.last_full()
        with mock.patch.object(self.cy, "sleep_a", return_value={"phase":"SLEEP_A","status":"INTERRUPTED"}) as a, \
             mock.patch("v13.sleep_offline.run", side_effect=AssertionError("offline after cancel")) as offline, \
             mock.patch.object(self.cy, "sleep_b", side_effect=AssertionError("B after cancel")) as b, \
             mock.patch.object(self.cy, "sleep_c", side_effect=AssertionError("C after cancel")) as c:
            rep = self.cy.run("full", origin="USER", resource=lambda: "NORMAL")
        self.assertEqual(rep["status"], "INTERRUPTED")
        self.assertEqual([p["phase"] for p in rep["phases"]], ["SLEEP_A"])
        self.assertEqual(self.last_full(), before)
        a.assert_called_once();offline.assert_not_called();b.assert_not_called();c.assert_not_called()

    def test_interrupted_offline_stops_b_c(self):
        before = self.last_full()
        with mock.patch.object(self.cy, "sleep_a", return_value={"phase":"SLEEP_A","status":"DONE"}), \
             mock.patch("v13.sleep_offline.run", return_value={"phase":"SLEEP_OFFLINE","status":"INTERRUPTED"}), \
             mock.patch.object(self.cy, "sleep_b", side_effect=AssertionError("B after offline cancel")) as b, \
             mock.patch.object(self.cy, "sleep_c", side_effect=AssertionError("C after offline cancel")) as c:
            rep = self.cy.run("full", origin="USER", resource=lambda: "NORMAL")
        self.assertEqual(rep["status"], "INTERRUPTED")
        self.assertEqual([p["phase"] for p in rep["phases"]], ["SLEEP_A", "SLEEP_OFFLINE"])
        self.assertEqual(self.last_full(), before)
        b.assert_not_called();c.assert_not_called()

    def test_interrupted_b_stops_c(self):
        before = self.last_full()
        with mock.patch.object(self.cy, "sleep_a", return_value={"phase":"SLEEP_A","status":"DONE"}), \
             mock.patch("v13.sleep_offline.run", return_value={"phase":"SLEEP_OFFLINE","status":"DONE"}), \
             mock.patch.object(self.cy, "sleep_b", return_value={"phase":"SLEEP_B","status":"INTERRUPTED"}) as b, \
             mock.patch.object(self.cy, "sleep_c", side_effect=AssertionError("C after B cancel")) as c:
            rep = self.cy.run("full", origin="USER", resource=lambda: "NORMAL")
        self.assertEqual(rep["status"], "INTERRUPTED")
        self.assertEqual(self.last_full(), before)
        b.assert_called_once();c.assert_not_called()

    def test_successful_full_advances_clock_and_survives_restart(self):
        before = self.last_full()
        with mock.patch.object(self.cy, "sleep_a", return_value={"phase":"SLEEP_A","status":"DONE"}), \
             mock.patch("v13.sleep_offline.run", return_value={"phase":"SLEEP_OFFLINE","status":"DONE"}), \
             mock.patch.object(self.cy, "sleep_b", return_value={"phase":"SLEEP_B","status":"DONE"}), \
             mock.patch.object(self.cy, "sleep_c", return_value={"phase":"SLEEP_C","status":"DONE"}):
            rep = self.cy.run("full", origin="USER", resource=lambda: "NORMAL")
        self.assertEqual(rep["status"], "DONE")
        self.assertGreater(self.last_full(), before)
        committed = self.last_full()
        self.r.close()
        self.r = Runtime(self.home)
        self.cy = self.r.sleep.cycle
        self.assertEqual(self.last_full(), committed)

    def test_direct_c_under_pressure_is_legitimate_done_without_full_credit(self):
        before = self.last_full()
        with mock.patch.object(self.cy, "sleep_c", return_value={"phase":"SLEEP_C","status":"DONE"}):
            rep = self.cy.run("c", origin="USER", resource=lambda: "PRESSURE")
        self.assertEqual(rep["status"], "DONE")
        self.assertEqual([p["phase"] for p in rep["phases"]], ["SLEEP_C"])
        self.assertEqual(self.last_full(), before)


if __name__ == "__main__":
    unittest.main()
