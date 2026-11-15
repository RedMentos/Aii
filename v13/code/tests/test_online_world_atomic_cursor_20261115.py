"""Regression: T8 cursor and numeric weights must share a checkpoint generation."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from v13.continuous_predictor import OnlinePredictor
from v13.online_world import OnlineWorld


class AtomicT8CursorTests(unittest.TestCase):
    def test_predictor_restart_reads_exact_cursor_and_weights(self):
        with tempfile.TemporaryDirectory() as td:
            p = OnlinePredictor(7, 2, td)
            x = np.zeros(7)
            y = np.ones(7)
            p.observe(x, 0, y)
            p.checkpoint(processed_ids=['trusted-a'])
            before = p.predict(x, 0).copy()
            q = OnlinePredictor(7, 2, td)
            self.assertEqual(q.processed_ids, ['trusted-a'])
            self.assertEqual(q.seen, 1)
            np.testing.assert_array_equal(q.predict(x, 0), before)

    def test_failed_replace_does_not_advance_durable_cursor(self):
        with tempfile.TemporaryDirectory() as td:
            p = OnlinePredictor(7, 2, td)
            x = np.zeros(7)
            p.observe(x, 0, np.ones(7))
            p.checkpoint(processed_ids=['trusted-a'])
            p.observe(x, 0, np.full(7, 2.))
            with patch('v13.continuous_predictor.os.replace', side_effect=OSError('simulated crash')):
                with self.assertRaises(OSError):
                    p.checkpoint(processed_ids=['trusted-a', 'trusted-b'])
            q = OnlinePredictor(7, 2, td)
            self.assertEqual(q.seen, 1)
            self.assertEqual(q.processed_ids, ['trusted-a'])

    def test_world_failed_checkpoint_retries_same_instance_once(self):
        class Runtime:
            def __init__(self, home):
                self.home = home
                self.store = object()
        from v13 import world_model
        row = {'action_id': 'trusted-a', 's': [0., 0., 0., 0.],
               'y': [1., 0., 0.], 'a': world_model.ACTIONS[0]}
        with tempfile.TemporaryDirectory() as td:
            rt = Runtime(Path(td))
            with patch('v13.online_world.world_model.transitions', return_value=[row]):
                world = OnlineWorld(rt)
                with patch('v13.continuous_predictor.os.replace', side_effect=OSError('crash')):
                    with self.assertRaises(OSError):
                        world.update()
                self.assertEqual(world.processed, [])
                self.assertEqual(world.model.seen, 0)
                self.assertEqual(world.update()['learned'], 1)
                self.assertEqual(world.model.seen, 1)
                self.assertEqual(world.update()['learned'], 0)

    def test_world_restarts_without_duplicate_learning(self):
        class Runtime:
            def __init__(self, home):
                self.home = home
                self.store = object()
        row = {'action_id': 'trusted-a', 's': [0., 0., 0., 0.],
               'y': [1., 0., 0.], 'a': None}
        from v13 import world_model
        row['a'] = world_model.ACTIONS[0]
        with tempfile.TemporaryDirectory() as td:
            rt = Runtime(Path(td))
            with patch('v13.online_world.world_model.transitions', return_value=[row]):
                first = OnlineWorld(rt)
                self.assertEqual(first.update()['learned'], 1)
                second = OnlineWorld(rt)
                self.assertEqual(second.update()['learned'], 0)
                self.assertEqual(second.model.seen, 1)


if __name__ == '__main__':
    unittest.main()
