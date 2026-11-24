"""Run46 zero-step World-JEPA must never masquerade as learned confidence.

Synthetic software only; no native model, no user authority or gate promotion.
"""
import hashlib
import io
from pathlib import Path
import tempfile
import unittest

import numpy as np

from v13 import world_jepa as wj
from v13 import world_jepa_shadow_checkpoint as cp

SOURCE = hashlib.sha256(b'run46 synthetic exact source').hexdigest()


class ZeroStepEvidenceGuard(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(20261028)
        self.x = rng.normal(size=(16, 6))
        self.a = np.tile(np.array([[1., 0.]]), (16, 1))
        self.x2 = self.x + .01
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'private-inference.npz'

    def model(self, steps):
        return wj.WorldJEPA(seed=7, ensemble=1).fit(
            self.x, self.a, self.x2, steps=steps, log_every=1)

    def test_zero_step_in_sample_action_cannot_claim_model_simulation(self):
        m = self.model(0)
        conf, labels = m.confidence(self.x[:1], self.a[:1])
        np.testing.assert_array_equal(conf, [0.])
        self.assertEqual(labels, ['SIMULATION_UNCERTAIN'])
        self.assertEqual(m._fit_steps, 0)

    def test_zero_step_control_cannot_export_as_trained_inference(self):
        m = self.model(0)
        with self.assertRaisesRegex(ValueError, 'zero-step|training-step|fit_steps'):
            cp.save(m, self.path, SOURCE)
        self.assertFalse(self.path.exists())

    def test_positive_step_roundtrip_preserves_step_bound_and_confidence(self):
        m = self.model(2)
        self.assertEqual(m._fit_steps, 2)
        record = cp.save(m, self.path, SOURCE)
        restored = cp.load(self.path, SOURCE, record['sha256'])
        self.assertEqual(restored._fit_steps, 2)
        self.assertEqual(record['schema'], cp.SCHEMA)
        c1, l1 = m.confidence(self.x[:2], self.a[:2])
        c2, l2 = restored.confidence(self.x[:2], self.a[:2])
        np.testing.assert_array_equal(c1, c2)
        self.assertEqual(l1, l2)

    def _archive(self, meta, arrays):
        stream = io.BytesIO()
        np.savez_compressed(stream, meta=np.frombuffer(cp._meta_json(meta), dtype=np.uint8), **arrays)
        self.path.write_bytes(stream.getvalue())
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_legacy_v1_inference_loads_but_has_no_learned_confidence(self):
        m = self.model(2)
        meta, arrays = cp._extract(m, SOURCE)
        meta['schema'] = cp.LEGACY_SCHEMA
        meta.pop('fit_steps', None)
        digest = self._archive(meta, arrays)
        old = cp.load(self.path, SOURCE, digest)
        self.assertEqual(old._fit_steps, 0)
        np.testing.assert_array_equal(old.latent(self.x[:2]), m.latent(self.x[:2]))
        conf, labels = old.confidence(self.x[:2], self.a[:2])
        np.testing.assert_array_equal(conf, np.zeros(2))
        self.assertEqual(labels, ['SIMULATION_UNCERTAIN'] * 2)

    def test_v2_zero_or_noninteger_fit_steps_rejected(self):
        m = self.model(2)
        meta, arrays = cp._extract(m, SOURCE)
        for bad in (0, -1, 1.5, True, '2'):
            with self.subTest(bad=bad):
                meta['fit_steps'] = bad
                digest = self._archive(meta, arrays)
                with self.assertRaises(ValueError):
                    cp.load(self.path, SOURCE, digest)


if __name__ == '__main__':
    unittest.main()
