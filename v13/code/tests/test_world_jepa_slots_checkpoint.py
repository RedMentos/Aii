"""Z12c persistent SHADOW World-JEPA: trained slot predictor survives restart.
Software/synthetic proof only; no native model, phone or factual write authority.
"""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from v13.world_jepa_slots import SlotWorldJEPA
from tests.test_world_jepa_slots import world, S

PROV = {'cohort_sha256': 'a'*64, 'source_sha256': 'b'*64}


class SlotWorldJEPACheckpoint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'slot-world-shadow.npz'
        self.X, self.A, self.X2 = world(60, np.random.default_rng(13))
        self.model = SlotWorldJEPA(S, seed=17, ensemble=2).fit(
            self.X, self.A, self.X2, steps=30, log_every=10).calibrate(
                self.X[40:], self.A[40:], self.X2[40:])

    def tearDown(self):
        self.tmp.cleanup()

    def test_prediction_confidence_and_error_are_identical_after_reload(self):
        saved = self.model.save(self.path, provenance=PROV)
        self.assertEqual(saved['sha256'], hashlib.sha256(self.path.read_bytes()).hexdigest())
        new = SlotWorldJEPA.load(self.path, expected_provenance=PROV, expected_sha256=saved['sha256'])
        for a, b in ((self.model.predict(self.X[:8], self.A[:8]),
                      new.predict(self.X[:8], self.A[:8])),
                     (self.model.confidence(self.X[:8], self.A[:8])[0],
                      new.confidence(self.X[:8], self.A[:8])[0]),
                     (self.model.slot_errors(self.X[:8], self.A[:8], self.X2[:8]),
                      new.slot_errors(self.X[:8], self.A[:8], self.X2[:8]))):
            if isinstance(a, tuple):
                for x, y in zip(a, b): np.testing.assert_array_equal(x, y)
            else:
                np.testing.assert_array_equal(a, b)
        self.assertEqual(new.confidence(self.X[:8], self.A[:8])[1],
                         self.model.confidence(self.X[:8], self.A[:8])[1])

    def test_wrong_provenance_and_corrupted_bytes_fail_closed(self):
        saved = self.model.save(self.path, provenance=PROV)
        with self.assertRaises(ValueError):
            SlotWorldJEPA.load(self.path, expected_provenance={'cohort_sha256': 'x'*64, 'source_sha256': 'b'*64}, expected_sha256=saved['sha256'])
        raw = bytearray(self.path.read_bytes())
        raw[len(raw)//2] ^= 0xff
        self.path.write_bytes(raw)
        with self.assertRaises((ValueError, OSError, EOFError)):
            SlotWorldJEPA.load(self.path, expected_provenance=PROV, expected_sha256=saved['sha256'])

    def test_untrained_save_and_unbound_load_refused(self):
        with self.assertRaises(ValueError):
            SlotWorldJEPA(S).save(self.path, provenance=PROV)
        self.model.save(self.path, provenance=PROV)
        with self.assertRaises(ValueError):
            SlotWorldJEPA.load(self.path)

    def test_atomic_failed_save_does_not_replace_last_checkpoint(self):
        self.model.save(self.path, provenance=PROV)
        before = self.path.read_bytes()
        with patch('v13.world_jepa_slots.atomic_write', side_effect=OSError('simulated interrupted write')):
            with self.assertRaises(OSError):
                self.model.save(self.path, provenance=PROV)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
