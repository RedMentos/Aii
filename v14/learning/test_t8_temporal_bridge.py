import tempfile
import unittest
from t8_temporal_bridge import TemporalT8Bridge


class TestBridge(unittest.TestCase):
    def test_observed_restart_replay_and_omission(self):
        with tempfile.TemporaryDirectory() as d:
            b = TemporalT8Bridge(d, learning_enabled=True)
            with self.assertRaises(PermissionError):
                b.open(event_id="x", source="T8:s", owner="WORLD", outcome="ok", opened_at=0, earliest=0, deadline=10, probability=.7)
            b.open(event_id="x", source="T8:s", owner="WORLD", outcome="ok", opened_at=0, earliest=0, deadline=10, probability=.7, trusted=True)
            result = b.observe(event_id="x", at=4, observed=True, evidence="T8:receipt", observed_outcome="ok", trusted=True, optimizer_permission=True)
            self.assertTrue(result["updated"]); self.assertGreater(result["parameter_delta"]["WORLD"], 0)
            again = TemporalT8Bridge(d, learning_enabled=True)
            self.assertTrue(again.observe(event_id="x", at=4, observed=True, evidence="T8:receipt", observed_outcome="ok", trusted=True, optimizer_permission=True)["duplicate"])
            with self.assertRaises(ValueError): again.observe(event_id="x", at=4, observed=True, evidence="T8:other", observed_outcome="ok", trusted=True, optimizer_permission=True)
            again.open(event_id="y", source="T8:s", owner="WORLD", outcome="ok", opened_at=0, earliest=0, deadline=10, probability=.7, trusted=True)
            omission = again.observe(event_id="y", at=11, observed=False, evidence="T8:complete", complete=True, trusted=True, optimizer_permission=True)
            self.assertLess(omission["parameter_delta"]["WORLD"], 0)

    def test_mismatched_outcome_updates_negative_error(self):
        with tempfile.TemporaryDirectory() as d:
            b = TemporalT8Bridge(d, learning_enabled=True)
            b.open(event_id="bad", source="T8:s", owner="WORLD", outcome="success", opened_at=0, earliest=0, deadline=10, probability=.8, trusted=True)
            result = b.observe(event_id="bad", at=5, observed=True, evidence="T8:failure", observed_outcome="failure", trusted=True, optimizer_permission=True)
            self.assertEqual(result["outcome"], "MISMATCHED")
            self.assertLess(result["parameter_delta"]["WORLD"], 0)

    def test_permission_and_delayed_optimizer(self):
        with tempfile.TemporaryDirectory() as d:
            b = TemporalT8Bridge(d, learning_enabled=True)
            b.open(event_id="x", source="T8:s", owner="WORLD", outcome="ok", opened_at=0, earliest=0, deadline=10, probability=.5, trusted=True)
            pending = b.observe(event_id="x", at=3, observed=True, evidence="T8:receipt", observed_outcome="ok", trusted=True)
            self.assertTrue(pending["pending_optimizer"]); self.assertEqual(b.receiver.seen, [])
            b = TemporalT8Bridge(d, learning_enabled=True)
            self.assertTrue(b.observe(event_id="x", at=3, observed=True, evidence="T8:receipt", observed_outcome="ok", trusted=True, optimizer_permission=True)["updated"])
            with self.assertRaises(PermissionError): b.observe(event_id="x", at=3, observed=True, evidence="T8:receipt", observed_outcome="ok")
            frozen = TemporalT8Bridge(d, learning_enabled=False)
            frozen.open(event_id="z", source="T8:s", owner="WORLD", outcome="ok", opened_at=0, earliest=0, deadline=10, probability=.5, trusted=True)
            with self.assertRaises(PermissionError): frozen.observe(event_id="z", at=3, observed=True, evidence="T8:receipt", observed_outcome="ok", trusted=True, optimizer_permission=True)

    def test_truthy_but_not_boolean_trust_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            b = TemporalT8Bridge(d, learning_enabled=True)
            with self.assertRaises(PermissionError):
                b.open(event_id="x", source="T8:s", owner="WORLD", outcome="ok", opened_at=0, earliest=0, deadline=10, probability=.5, trusted="yes")
            with self.assertRaises(ValueError):
                b.observe(event_id="x", at=1, observed=False, evidence="", trusted=True, optimizer_permission="yes")


if __name__ == "__main__": unittest.main()
