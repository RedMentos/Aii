"""Host-only synthetic teacher provenance, retention, restart and A5 tests."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from dataclasses import replace

from v13.a3_online_projector import A3Projector
from v13.a3_evidence_bridge import A3EvidenceBridge, TeacherEvidence


def evidence(x, y, *, source="fixture-1", final=True, scope="a3_train"):
    e = TeacherEvidence(source, "frozen-a2-fixture-v1", tuple(x), tuple(y),
                        final, scope, "")
    return replace(e, content_sha256=hashlib.sha256(e.canonical_bytes()).hexdigest())


class TestA3EvidenceBridge(unittest.TestCase):
    def test_learn_percept_restart(self):
        p = A3Projector(2, 1, .05)
        valid = {"fixture-1"}
        bridge = A3EvidenceBridge(p, lambda e: e.source_id in valid)
        train = [evidence([1.,0.],[.6]), evidence([0.,1.],[-.4]),
                 evidence([1.,1.],[.2])]
        hold = evidence([.5,.5],[.1])
        before = abs(bridge.percept(hold)["a3_embedding"][0]-.1)
        for _ in range(200):
            for item in train:
                bridge.learn(item)
        packet = bridge.percept(hold)
        self.assertLess(abs(packet["a3_embedding"][0]-.1), before*.1)
        self.assertEqual(packet["authority"], "observation_only")
        self.assertFalse(packet["android_action_allowed"])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"a3.json"
            p.save(path)
            restored = A3EvidenceBridge(A3Projector.load(path), lambda e: e.source_id in valid)
            self.assertEqual(restored.percept(hold)["a3_embedding"], packet["a3_embedding"])
            valid.clear()
            with self.assertRaises(PermissionError):
                restored.percept(hold)

    def test_reject_untrusted_provisional_tampered(self):
        p = A3Projector(2,1)
        bridge = A3EvidenceBridge(p, lambda e: e.source_id == "fixture-1")
        for item in (evidence([1.,0.],[.6],source="revoked"),
                     evidence([1.,0.],[.6],final=False),
                     evidence([1.,0.],[.6],scope="observe"),
                     replace(evidence([1.,0.],[.6]), target_vector=(.9,))):
            with self.assertRaises((PermissionError,ValueError)):
                bridge.learn(item)
        self.assertEqual(p.steps, 0)

    def test_no_unverified_percept_or_nan(self):
        bridge = A3EvidenceBridge(A3Projector(2,1), lambda e: False)
        with self.assertRaises(PermissionError):
            bridge.percept(evidence([1.,0.],[.6]))
        with self.assertRaises(ValueError):
            bridge.learn(evidence([float("nan"),0.],[.6]))


if __name__ == "__main__":
    unittest.main()
