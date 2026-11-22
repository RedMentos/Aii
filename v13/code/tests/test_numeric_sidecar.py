"""Synthetic-only numeric sidecar contract regression tests."""
import unittest
from v13.latent_bridge import Projector
from v13.numeric_sidecar import NumericSidecar

class NumericSidecarTests(unittest.TestCase):
    def setUp(self):
        self.p = Projector("A3", "B3", 2, 2)
        self.p.update([1, 0], [.5, -.5], admitted=True, committed=True)
        self.s = NumericSidecar(self.p, encoder_revision="encoder-v1", receiver_revision="receiver-v1")
        self.e = {"event_id": "turn-1", "brain_generation_id": "age0-gen1"}

    def send(self):
        return self.s.send(self.e, source_id="source-1", source_vector=[1, 0],
                           sender_revision="encoder-v1", consent_active=True)

    def take(self, receipt, **kwargs):
        return self.s.take(self.e, receipt, receiver_revision="receiver-v1",
                           admitted_source_ids=["source-1"], consent_active=True, **kwargs)

    def test_numeric_transfer_and_one_shot(self):
        receipt = self.send()
        self.assertEqual(len(self.take(receipt)), 2)
        with self.assertRaises(ValueError):
            self.take(receipt)

    def test_no_consent(self):
        with self.assertRaises(PermissionError):
            self.s.send(self.e, source_id="source-1", source_vector=[1, 0],
                        sender_revision="encoder-v1")
        receipt = self.send()
        with self.assertRaises(PermissionError):
            self.s.take(self.e, receipt, receiver_revision="receiver-v1",
                        admitted_source_ids=["source-1"])

    def test_no_cross_event_or_generation(self):
        receipt = self.send()
        self.e["event_id"] = "turn-2"
        with self.assertRaises(PermissionError):
            self.take(receipt)
        self.e["event_id"] = "turn-1"
        self.e["brain_generation_id"] = "age0-gen2"
        with self.assertRaises(PermissionError):
            self.take(receipt)

    def test_no_unadmitted_source(self):
        receipt = self.send()
        with self.assertRaises(PermissionError):
            self.s.take(self.e, receipt, receiver_revision="receiver-v1",
                        admitted_source_ids=["other"], consent_active=True)

    def test_revision_and_integrity(self):
        receipt = self.send()
        with self.assertRaises(ValueError):
            self.s.take(self.e, receipt, receiver_revision="receiver-v2",
                        admitted_source_ids=["source-1"], consent_active=True)
        self.p.update([1, 0], [0, 1], admitted=True, committed=True)
        with self.assertRaises(ValueError):
            self.take(receipt)

    def test_reject_unversioned_or_invalid_vector(self):
        with self.assertRaises(ValueError):
            NumericSidecar(self.p, encoder_revision="", receiver_revision="r1")
        with self.assertRaises(ValueError):
            self.s.send(self.e, source_id="source-1", source_vector=[float("nan"), 0],
                        sender_revision="encoder-v1", consent_active=True)

    def test_discard(self):
        receipt = self.send()
        self.s.discard_event(self.e)
        with self.assertRaises(ValueError):
            self.take(receipt)

if __name__ == "__main__":
    unittest.main()
