"""Disjoint trusted T8 holdout utility against the real OnlineWorld adapter."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13 import world_model
from v13.online_world import OnlineWorld


class Runtime:
    def __init__(self, home):
        self.home = Path(home)
        self.store = object()


def transition(identifier, target):
    return {'action_id': identifier, 's': [0., 0., 0., 0.],
            'y': [float(target), 0., 0.], 'a': world_model.ACTIONS[0]}


class DisjointHoldoutTests(unittest.TestCase):
    def test_training_reduces_disjoint_holdout_error_and_survives_restart(self):
        train = [transition('train-%d' % i, 1.) for i in range(24)]
        holdout = [transition('holdout-%d' % i, 1.) for i in range(5)]
        with tempfile.TemporaryDirectory() as home:
            rt = Runtime(home)
            world = OnlineWorld(rt)
            before = world.evaluate_disjoint_holdout(holdout)['mse']
            with patch('v13.online_world.world_model.transitions', return_value=train):
                self.assertEqual(world.update()['learned'], len(train))
            after = world.evaluate_disjoint_holdout(holdout)['mse']
            self.assertLess(after, before)
            restarted = OnlineWorld(rt)
            self.assertAlmostEqual(restarted.evaluate_disjoint_holdout(holdout)['mse'], after)
            self.assertEqual(restarted.model.seen, len(train))

    def test_holdout_evaluation_never_trains_or_advances_cursor(self):
        with tempfile.TemporaryDirectory() as home:
            world = OnlineWorld(Runtime(home))
            before = (world.model.seen, world.model.updates, list(world.processed))
            self.assertEqual(world.evaluate_disjoint_holdout(
                [transition('holdout', 1.)])['status'], 'DISJOINT_HOLDOUT_READ_ONLY')
            self.assertEqual((world.model.seen, world.model.updates, world.processed), before)

    def test_rejects_overlap_duplicates_and_empty_holdout(self):
        with tempfile.TemporaryDirectory() as home:
            rt = Runtime(home)
            world = OnlineWorld(rt)
            with patch('v13.online_world.world_model.transitions',
                       return_value=[transition('trained', 1.)]):
                world.update()
            for rows in ([], [transition('trained', 1.)],
                         [transition('same', 1.), transition('same', 1.)]):
                with self.subTest(rows=rows):
                    with self.assertRaises(ValueError):
                        world.evaluate_disjoint_holdout(rows)


if __name__ == '__main__':
    unittest.main()
