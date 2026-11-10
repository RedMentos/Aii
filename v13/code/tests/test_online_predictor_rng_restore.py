"""Synthetic restart integrity: reject bad RNG without partial state publication.

Run: cd v13/code && python -m unittest tests.test_online_predictor_rng_restore
No native/Android evidence.
"""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from v13.continuous_predictor import OnlinePredictor


class PredictorRngRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.model = OnlinePredictor(3, 2, self.home, replay=4, seed=19)
        self.model.observe([0.2, 0, 0], 0, [0.3, 0, 0])
        self.model.checkpoint(processed_ids=['trusted-action'])

    def test_invalid_rng_rejects_without_partial_restore(self):
        with np.load(self.model.path, allow_pickle=False) as data:
            payload = {key: data[key].copy() for key in data.files}
        payload['rng_state'] = np.array(json.dumps({'bit_generator': 'INVALID'}))
        np.savez_compressed(self.model.path, **payload)
        # The live model intentionally differs from the on-disk snapshot.
        self.model.W[0, 0] = 123.0
        self.model.seen = 42
        self.model.checkpoint_ids = ['live']
        before_rng = json.dumps(self.model.rng.bit_generator.state, sort_keys=True)
        with self.assertRaisesRegex(ValueError, 'Invalid predictor checkpoint RNG state'):
            self.model.restore()
        self.assertEqual(self.model.W[0, 0], 123.0)
        self.assertEqual(self.model.seen, 42)
        self.assertEqual(self.model.checkpoint_ids, ['live'])
        self.assertEqual(json.dumps(self.model.rng.bit_generator.state, sort_keys=True), before_rng)

    def test_valid_rng_restart_reproduces_next_sample(self):
        expected = self.model.rng.integers(0, 100000, size=8).tolist()
        restored = OnlinePredictor(3, 2, self.home, replay=4, seed=999)
        self.assertEqual(restored.rng.integers(0, 100000, size=8).tolist(), expected)
        self.assertEqual(restored.checkpoint_ids, ['trusted-action'])


if __name__ == '__main__':
    unittest.main()
