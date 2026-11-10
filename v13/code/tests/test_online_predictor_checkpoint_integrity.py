"""Fail-closed checkpoint integrity tests for bounded local predictor plasticity.

Run: cd v13/code && python -m unittest tests.test_online_predictor_checkpoint_integrity
Synthetic NumPy-only tests; no native models or Android evidence.
"""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from v13.continuous_predictor import OnlinePredictor


class PredictorCheckpointIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.model = OnlinePredictor(3, 2, self.home, replay=4)
        self.model.observe([0.1, 0, 0], 0, [0.2, 0, 0])
        self.model.checkpoint(processed_ids=['trusted-one'])

    def corrupt(self, key, value):
        with np.load(self.model.path, allow_pickle=False) as data:
            payload = {name: data[name].copy() for name in data.files}
        payload[key] = value
        np.savez_compressed(self.model.path, **payload)

    def test_valid_checkpoint_restarts(self):
        restored = OnlinePredictor(3, 2, self.home, replay=4)
        self.assertEqual(restored.seen, 1)
        self.assertEqual(restored.checkpoint_ids, ['trusted-one'])

    def test_fractional_counters_rejected(self):
        self.corrupt('counters', np.array([1.5, 3.0]))
        with self.assertRaisesRegex(ValueError, 'Invalid predictor checkpoint'):
            OnlinePredictor(3, 2, self.home, replay=4)

    def test_seen_smaller_than_replay_rejected(self):
        self.corrupt('counters', np.array([0, 3], dtype=np.int64))
        with self.assertRaisesRegex(ValueError, 'Invalid predictor checkpoint'):
            OnlinePredictor(3, 2, self.home, replay=4)

    def test_updates_smaller_than_seen_rejected(self):
        self.corrupt('counters', np.array([2, 1], dtype=np.int64))
        with self.assertRaisesRegex(ValueError, 'Invalid predictor checkpoint'):
            OnlinePredictor(3, 2, self.home, replay=4)

    def test_out_of_range_replay_rejected(self):
        with np.load(self.model.path, allow_pickle=False) as data:
            x = data['x'].copy()
        x[0, 0] = 1e6 + 1
        self.corrupt('x', x)
        with self.assertRaisesRegex(ValueError, 'Invalid predictor checkpoint'):
            OnlinePredictor(3, 2, self.home, replay=4)


if __name__ == '__main__':
    unittest.main()
