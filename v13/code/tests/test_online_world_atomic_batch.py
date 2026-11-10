"""Atomic OnlineWorld regression checks: batch validation and cursor/weight parity.

Run: cd v13/code && python -m unittest tests.test_online_world_atomic_batch
No native weights or Android hardware required.
"""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from v13.online_world import OnlineWorld
from v13 import world_model


def row(action_id, outcome=None):
    return {
        'action_id': action_id,
        's': [0.1, 0.0, 0.0, 1.0],
        'a': 'simple',
        'y': [0.1, 1.0, 0.2] if outcome is None else outcome,
    }


class AtomicOnlineWorldTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runtime = SimpleNamespace(home=Path(self.tmp.name), store=object())

    def test_later_bad_transition_cannot_partially_train(self):
        learner = OnlineWorld(self.runtime)
        before = learner.model.W.copy()
        with patch.object(world_model, 'transitions', return_value=[
            row('valid'), row('invalid', [float('nan'), 0.0, 1.0])
        ]):
            with self.assertRaises(ValueError):
                learner.update()
        self.assertEqual(learner.model.seen, 0)
        self.assertEqual(learner.processed, [])
        np.testing.assert_array_equal(learner.model.W, before)
        self.assertFalse(learner.model.path.exists())

    def test_atomic_checkpoint_restarts_without_relearning(self):
        learner = OnlineWorld(self.runtime)
        with patch.object(world_model, 'transitions', return_value=[row('one')]):
            self.assertEqual(learner.update()['learned'], 1)
        # A stale legacy sidecar cannot override IDs embedded with weights.
        learner.cursor.write_text(json.dumps({'revision': 'v13-online-world-v1',
                                              'processed': []}))
        restarted = OnlineWorld(self.runtime)
        self.assertEqual(restarted.processed, ['one'])
        with patch.object(world_model, 'transitions', return_value=[row('one')]):
            self.assertEqual(restarted.update()['learned'], 0)
        self.assertEqual(restarted.model.seen, 1)

    def test_missing_cursor_for_existing_legacy_weights_fails_closed(self):
        learner = OnlineWorld(self.runtime)
        learner.model.observe(*OnlineWorld.encode(row('one')))
        learner.model.checkpoint()  # Legacy checkpoint without embedded IDs
        with self.assertRaisesRegex(ValueError, 'checkpoint/cursor mismatch'):
            OnlineWorld(self.runtime)

    def test_legacy_cursor_ahead_of_weights_fails_closed(self):
        learner = OnlineWorld(self.runtime)
        learner.cursor.write_text(json.dumps({'revision': 'v13-online-world-v1',
                                              'processed': ['not-learned']}))
        with self.assertRaisesRegex(ValueError, 'checkpoint/cursor mismatch'):
            OnlineWorld(self.runtime)


if __name__ == '__main__':
    unittest.main()
