"""Regression: invalid later T8 rows must not cause partial online learning."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from v13 import world_model
from v13.online_world import OnlineWorld


class OnlineWorldBatchValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runtime = SimpleNamespace(home=Path(self.tmp.name), store=object())

    @staticmethod
    def row(action_id, valid=True):
        return {
            'action_id': action_id,
            's': [0.0, 0.1, 0.2, 0.3],
            'a': world_model.ACTIONS[0],
            'y': [0.4, 0.5, 0.6] if valid else [float('nan'), 0.5, 0.6],
        }

    def test_invalid_second_row_does_not_partially_learn_first(self):
        learner = OnlineWorld(self.runtime)
        with patch.object(world_model, 'transitions', return_value=[
            self.row('committed-a'), self.row('committed-b', valid=False)
        ]):
            with self.assertRaisesRegex(ValueError, 'Invalid committed T8 transition'):
                learner.update()
        self.assertEqual(learner.model.seen, 0)
        self.assertEqual(learner.model.updates, 0)
        self.assertEqual(learner.processed, [])
        self.assertFalse(learner.cursor.exists())
        restored = OnlineWorld(self.runtime)
        self.assertEqual(restored.model.seen, 0)

    def test_valid_batch_restart_and_duplicate_replay_are_idempotent(self):
        rows = [self.row('committed-a'), self.row('committed-b')]
        learner = OnlineWorld(self.runtime)
        with patch.object(world_model, 'transitions', return_value=rows):
            first = learner.update()
        self.assertEqual(first['learned'], 2)
        self.assertEqual(first['seen'], 2)
        restored = OnlineWorld(self.runtime)
        with patch.object(world_model, 'transitions', return_value=rows):
            second = restored.update()
        self.assertEqual(second['learned'], 0)
        self.assertEqual(second['seen'], 2)
        self.assertEqual(second['tracked_ids'], 2)

    def test_reject_invalid_row_even_when_earlier_row_is_valid(self):
        learner = OnlineWorld(self.runtime)
        malformed = self.row('committed-b')
        malformed['a'] = 'not-a-registered-action'
        with patch.object(world_model, 'transitions', return_value=[
            self.row('committed-a'), malformed
        ]):
            with self.assertRaises(ValueError):
                learner.update()
        self.assertEqual(learner.model.seen, 0)


if __name__ == '__main__':
    unittest.main()
