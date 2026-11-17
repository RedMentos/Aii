"""Regression: numeric B3 sidecar must not grow without bound on Android."""
import unittest
from v13.latent_bridge import Projector
from v13.numeric_sidecar import NumericSidecar

class BoundedPendingTest(unittest.TestCase):
    def setUp(self):
        self.p = Projector("B1", "B2", 2, 2)
        self.s = NumericSidecar(self.p, encoder_revision="enc1", receiver_revision="recv1", max_pending=2)
    def event(self, n):
        return {"event_id": "event"+str(n), "brain_generation_id": "gen1"}
    def send(self, n):
        return self.s.send(self.event(n), source_id="src"+str(n),
                           source_vector=[1., 2.], sender_revision="enc1",
                           consent_active=True)
    def test_capacity_and_explicit_release(self):
        self.send(1); self.send(2)
        with self.assertRaises(OverflowError): self.send(3)
        self.assertEqual(len(self.s._pending), 2)
        self.s.discard_event(self.event(1))
        self.send(3)
        self.assertEqual(len(self.s._pending), 2)
    def test_one_shot_receive_frees_slot(self):
        receipt = self.send(1)
        self.send(2)
        values = self.s.take(self.event(1), receipt, receiver_revision="recv1",
                             admitted_source_ids=["src1"], consent_active=True)
        self.assertEqual(len(values), 2)
        self.send(3)
        with self.assertRaises(ValueError):
            self.s.take(self.event(1), receipt, receiver_revision="recv1",
                        admitted_source_ids=["src1"], consent_active=True)
    def test_same_identity_overwrite_does_not_use_extra_slot(self):
        self.send(1); self.send(2); self.send(1)
        self.assertEqual(len(self.s._pending), 2)
    def test_capacity_configuration_rejects_unbounded(self):
        for value in (0, -1, 4097, 2.5, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                NumericSidecar(self.p, encoder_revision="enc1",
                               receiver_revision="recv1", max_pending=value)
    def test_no_consent_does_not_enqueue(self):
        with self.assertRaises(PermissionError):
            self.s.send(self.event(1), source_id="src1",
                        source_vector=[1, 2], sender_revision="enc1")
        self.assertEqual(len(self.s._pending), 0)

if __name__ == "__main__":
    unittest.main()
