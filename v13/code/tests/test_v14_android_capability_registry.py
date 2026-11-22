"""V14 Android capability E2E: offline SQLite simulation, never device proof."""
import tempfile
import unittest
from pathlib import Path

from v13.android_control import AndroidControlBroker, ControlDenied
from v13.android_capability_registry import CapabilityRegistry, simulated_registry


class CapabilityPipelineTests(unittest.TestCase):
    def test_default_off_and_no_implicit_native(self):
        r = CapabilityRegistry()
        s = r.status()
        self.assertEqual(s["native_transport"], "OFF")
        self.assertTrue(all(x["mode"] == "OFF" and not x["android_verified"]
                            for x in s["capabilities"]))
        with tempfile.TemporaryDirectory() as d:
            b = AndroidControlBroker(Path(d) / "audit.db")
            b.start()
            p = b.propose("observe_ui", {})
            b.approve(p.action_id, confirmed_by_local_ui=True)
            with self.assertRaises(ControlDenied):
                r.execute_approved(b, p.action_id)
            b.close()

    def test_approved_action_outcome_restart_and_replay(self):
        with tempfile.TemporaryDirectory() as d:
            b = AndroidControlBroker(Path(d) / "audit.db")
            r = simulated_registry(d)
            self.assertTrue(all(x["mode"] == "SIMULATED_ONLY"
                                for x in r.status()["capabilities"]))
            b.start()
            with self.assertRaises(ControlDenied):
                b.approve(b.propose("launch_app", {"package": "org.v13.demo.notes"}).action_id)
            p = b.propose("launch_app", {"package": "org.v13.demo.notes"})
            b.approve(p.action_id, confirmed_by_local_ui=True)
            result = r.execute_approved(b, p.action_id)
            self.assertEqual(result["outcome"]["action_id"], p.action_id)
            self.assertEqual(result["outcome"]["status"], "SIMULATED")
            self.assertFalse(result["native_android_executed"])
            self.assertEqual(r.simulator.view()["screen"], "NOTES")
            self.assertEqual(len(r.simulator.transitions()), 1)
            with self.assertRaises(ControlDenied):
                r.execute_approved(b, p.action_id)
            r.close()
            r = simulated_registry(d)
            self.assertEqual(r.simulator.view()["screen"], "NOTES")
            self.assertEqual(r.simulator.receipt_count(), 1)
            r.close()
            b.close()

    def test_stop_denies_and_does_not_mutate(self):
        with tempfile.TemporaryDirectory() as d:
            b = AndroidControlBroker(Path(d) / "audit.db")
            r = simulated_registry(d)
            b.start()
            p = b.propose("observe_ui", {})
            b.approve(p.action_id, confirmed_by_local_ui=True)
            b.stop()
            with self.assertRaises(ControlDenied):
                r.execute_approved(b, p.action_id)
            self.assertEqual(r.simulator.receipt_count(), 0)
            r.close()
            b.close()


if __name__ == "__main__":
    unittest.main()
