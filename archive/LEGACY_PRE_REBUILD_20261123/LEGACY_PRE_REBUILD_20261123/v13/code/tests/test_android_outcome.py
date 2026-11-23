"""Offline contract tests: no Android permission or device execution."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from v13.android_control import AndroidControlBroker
from v13.android_outcome import InvalidOutcome, receipt, SCHEMA


class OutcomeTests(unittest.TestCase):
    def test_approved_dry_run_receipt_is_not_native(self):
        with tempfile.TemporaryDirectory() as d:
            broker = AndroidControlBroker(pathlib.Path(d) / "audit.db")
            broker.start()
            p = broker.propose("launch_app", {"package": "org.example.app"})
            broker.approve(p.action_id, confirmed_by_local_ui=True)
            result = receipt(broker.execute(p.action_id))
            self.assertEqual(result.as_record()["schema"], SCHEMA)
            self.assertEqual((result.status, result.origin), ("SIMULATED", "simulator"))
            with self.assertRaises(Exception):
                broker.execute(p.action_id)
            broker.close()

    def test_tampering_and_false_android_success_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            broker = AndroidControlBroker(pathlib.Path(d) / "audit.db")
            broker.start()
            p = broker.propose("tap", {"x": 10, "y": 20})
            broker.approve(p.action_id, confirmed_by_local_ui=True)
            envelope = broker.execute(p.action_id)
            for changed in ({"args": {"x": 11, "y": 20}},
                            {"digest": "0" * 64}, {"action_id": "invalid"},
                            {"status": "SUCCEEDED"}):
                with self.subTest(changed=changed), self.assertRaises(InvalidOutcome):
                    receipt({**envelope, **changed})
            for kwargs in ({"status": "SUCCEEDED"}, {"origin": "android"},
                           {"observed_at": -1}):
                with self.subTest(kwargs=kwargs), self.assertRaises(InvalidOutcome):
                    receipt(envelope, **kwargs)
            broker.close()


if __name__ == "__main__":
    unittest.main()
