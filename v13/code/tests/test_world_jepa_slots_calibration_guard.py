"""Independent Z12c review: absent operation-error calibration is not zero error."""
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from v13.world_jepa_slots import SlotWorldJEPA, CHECKPOINT_REVISION
from tests.test_world_jepa_slots import world, S

PROV = {'cohort_sha256': 'a'*64, 'source_sha256': 'b'*64}


class CalibrationRequiredZ12c(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'slot-shadow.npz'
        self.X, self.A, self.X2 = world(60, np.random.default_rng(13))
        self.m = SlotWorldJEPA(S, seed=17, ensemble=2).fit(
            self.X, self.A, self.X2, steps=30, log_every=10)

    def tearDown(self):
        self.tmp.cleanup()

    def missing_class_actions(self):
        a = np.zeros_like(self.A)
        a[:, :, -1] = 1.
        return a

    def test_uncalibrated_confidence_fails_closed(self):
        with self.assertRaises(ValueError):
            self.m.confidence(self.X[:3], self.A[:3])

    def test_uncalibrated_checkpoint_is_refused(self):
        with self.assertRaises(ValueError):
            self.m.save(self.path, provenance=PROV)
        self.assertFalse(self.path.exists())

    def test_missing_operation_calibration_cannot_be_authority(self):
        with self.assertRaises(ValueError):
            self.m.calibrate(self.X, self.missing_class_actions(), self.X2)
        with self.assertRaises(ValueError):
            self.m.confidence(self.X[:3], self.A[:3])

    def test_successful_calibration_persists_explicit_v2_authority(self):
        self.m.calibrate(self.X[40:], self.A[40:], self.X2[40:])
        before = self.m.confidence(self.X[:5], self.A[:5])
        saved = self.m.save(self.path, provenance=PROV)
        with np.load(self.path, allow_pickle=False) as z:
            meta = json.loads(z['meta'].tobytes().decode('utf8'))
        self.assertEqual(meta['checkpoint_revision'], 'z12c-slot-world-jepa-inference-npz-v2')
        self.assertTrue(meta['calibration_complete'])
        self.assertEqual(CHECKPOINT_REVISION, meta['checkpoint_revision'])
        reloaded = SlotWorldJEPA.load(self.path, expected_provenance=PROV, expected_sha256=saved['sha256'])
        after = reloaded.confidence(self.X[:5], self.A[:5])
        np.testing.assert_array_equal(before[0], after[0])
        self.assertEqual(before[1], after[1])

    def test_failed_later_calibration_revokes_previous_authority(self):
        self.m.calibrate(self.X[40:], self.A[40:], self.X2[40:])
        self.assertEqual(len(self.m.confidence(self.X[:2], self.A[:2])[0]), 2)
        with self.assertRaises(ValueError):
            self.m.calibrate(self.X, self.missing_class_actions(), self.X2)
        with self.assertRaises(ValueError):
            self.m.confidence(self.X[:2], self.A[:2])
        with self.assertRaises(ValueError):
            self.m.save(self.path, provenance=PROV)

    def test_old_v1_checkpoint_fails_closed_even_with_new_matching_digest(self):
        self.m.calibrate(self.X[40:], self.A[40:], self.X2[40:])
        self.m.save(self.path, provenance=PROV)
        with np.load(self.path, allow_pickle=False) as z:
            arrays = {name: z[name] for name in z.files}
        meta = json.loads(arrays['meta'].tobytes().decode('utf8'))
        meta['checkpoint_revision'] = 'z12c-slot-world-jepa-inference-npz-v1'
        arrays['meta'] = np.frombuffer(json.dumps(meta).encode('utf8'), dtype=np.uint8)
        np.savez_compressed(self.path, **arrays)
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            SlotWorldJEPA.load(self.path, expected_provenance=PROV, expected_sha256=digest)


if __name__ == '__main__':
    unittest.main()
