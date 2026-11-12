"""Feature-only A3 synthetic runtime integration and restart tests."""
import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from v13.a3_online_projector import A3Projector
from v13.a3_runtime_adapter import A3InferenceRuntime, FeatureObservation


def fixture(features=(.25, .5), *, final=True, source="approved", modality="synthetic_audio"):
    o = FeatureObservation(source, modality, tuple(features), final, "")
    return replace(o, feature_sha256=hashlib.sha256(o.canonical_bytes()).hexdigest())


class TestA3RuntimeAdapter(unittest.TestCase):
    def test_inference_checkpoint_restart_and_organ_views(self):
        p = A3Projector(2, 1, .05)
        for _ in range(100):
            p.train([1., 0.], [.5], trusted=True)
        approved = {"approved"}
        adapter = A3InferenceRuntime(p, lambda o: o.source_id in approved)
        first = adapter.observe(fixture())
        self.assertEqual(set(first), {"a5", "b1", "b2", "jef"})
        self.assertEqual(first["a5"]["a3_embedding"], first["b1"]["embedding"])
        self.assertFalse(first["jef"]["android_action_allowed"])
        self.assertNotIn("target_vector", str(first))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "weights.json"
            p.save(path)
            restored = A3InferenceRuntime(A3Projector.load(path), lambda o: o.source_id in approved)
            self.assertEqual(first, restored.observe(fixture()))
            approved.clear()
            with self.assertRaises(PermissionError):
                restored.observe(fixture())

    def test_provisional_tamper_and_invalid_modality(self):
        adapter = A3InferenceRuntime(A3Projector(2, 1), lambda o: True)
        with self.assertRaises(PermissionError):
            adapter.observe(fixture(final=False))
        with self.assertRaises(ValueError):
            adapter.observe(replace(fixture(), feature_vector=(.9, .5)))
        with self.assertRaises(ValueError):
            adapter.observe(fixture(modality="android_action"))
        with self.assertRaises(ValueError):
            adapter.observe(fixture(features=(float("nan"), .5)))

    def test_external_verifier_is_mandatory(self):
        with self.assertRaises(TypeError):
            A3InferenceRuntime(A3Projector(2, 1), None)
        with self.assertRaises(PermissionError):
            A3InferenceRuntime(A3Projector(2, 1), lambda o: False).observe(fixture())


if __name__ == "__main__":
    unittest.main()
