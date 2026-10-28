"""World-JEPA inference checkpoint: exact NumPy state, no training resume/age authority."""
import hashlib
import io
from pathlib import Path
import tempfile
import unittest

import numpy as np

from v13 import world_jepa as wj
from v13 import world_jepa_shadow_checkpoint as cp

SOURCE = hashlib.sha256(b'fixed synthetic source revision').hexdigest()


def fitted():
    rng = np.random.default_rng(20261028)
    X = rng.normal(size=(80, 8))
    actions = rng.integers(0, 4, size=len(X))
    A = np.eye(4)[actions]
    X2 = X.copy()
    X2[np.arange(len(X)), actions] += .5
    model = wj.WorldJEPA(seed=7, ensemble=2).fit(X, A, X2, steps=20, log_every=10)
    return model, X, A


class WorldJepaShadowCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'fitted-shadow.npz'

    def test_exact_inference_roundtrip_and_no_authority(self):
        model, X, A = fitted()
        record = cp.save(model, self.path, SOURCE)
        self.assertEqual(record['scope'], 'PRIVATE_INFERENCE_ONLY_SHADOW')
        self.assertEqual(record['age_authority'], 0)
        self.assertFalse(record['optimizer_state_persisted'])
        self.assertEqual(record['sha256'], hashlib.sha256(self.path.read_bytes()).hexdigest())
        restored = cp.load(self.path, SOURCE, record['sha256'])
        for target in (True, False):
            np.testing.assert_array_equal(restored.latent(X[:8], target=target),
                                          model.latent(X[:8], target=target))
        for got, expected in zip(restored.predict(X[:8], A[:8]),
                                 model.predict(X[:8], A[:8])):
            np.testing.assert_array_equal(got, expected)
        np.testing.assert_array_equal(restored.ood(X[:8]), model.ood(X[:8]))
        c1, labels1 = model.confidence(X[:8], A[:8])
        c2, labels2 = restored.confidence(X[:8], A[:8])
        np.testing.assert_array_equal(c1, c2)
        self.assertEqual(labels1, labels2)
        self.assertEqual(restored.history, [])

    def test_external_pins_tamper_and_overwrite_fail_closed(self):
        model, _, _ = fitted()
        record = cp.save(model, self.path, SOURCE)
        original = self.path.read_bytes()
        with self.assertRaises(ValueError):
            cp.save(model, self.path, SOURCE)
        self.assertEqual(original, self.path.read_bytes())
        with self.assertRaises(ValueError):
            cp.load(self.path, '0' * 64, record['sha256'])
        with self.assertRaises(ValueError):
            cp.load(self.path, SOURCE, 'f' * 64)
        self.path.write_bytes(original + b'X')
        with self.assertRaises(ValueError):
            cp.load(self.path, SOURCE, record['sha256'])
        self.path.write_bytes(original)
        alias = self.root / 'alias.npz'
        alias.symlink_to(self.path)
        with self.assertRaises(ValueError):
            cp.load(alias, SOURCE, record['sha256'])

    def test_nonfinite_and_incomplete_model_cannot_publish(self):
        model, _, _ = fitted()
        model.enc['W1'][0, 0] = float('nan')
        with self.assertRaises(ValueError):
            cp.save(model, self.path, SOURCE)
        self.assertFalse(self.path.exists())
        model.enc['W1'][0, 0] = 0.
        model.preds.pop()
        with self.assertRaises(ValueError):
            cp.save(model, self.path, SOURCE)
        self.assertFalse(self.path.exists())

    def test_hash_consistent_but_incomplete_archive_is_rejected(self):
        meta = {'schema': cp.SCHEMA, 'source_sha256': SOURCE,
                'model_revision': wj.REVISION, 'seed': 7, 'ensemble': 2}
        raw_meta = cp._meta_json(meta)
        stream = io.BytesIO()
        np.savez_compressed(stream, meta=np.frombuffer(raw_meta, dtype=np.uint8),
                            mu=np.zeros(8))
        self.path.write_bytes(stream.getvalue())
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            cp.load(self.path, SOURCE, digest)

    def test_invalid_source_and_destination_refused(self):
        model, _, _ = fitted()
        with self.assertRaises(ValueError):
            cp.save(model, self.path, 'bad')
        missing = self.root / 'nonexistent' / 'fitted.npz'
        with self.assertRaises(ValueError):
            cp.save(model, missing, SOURCE)
        self.assertFalse(self.path.exists())


if __name__ == '__main__':
    unittest.main()
