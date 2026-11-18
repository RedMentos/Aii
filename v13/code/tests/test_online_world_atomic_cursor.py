"""Crash/restart regression for source-bound T8 numeric learner (synthetic Linux)."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from v13.online_world import OnlineWorld
from v13 import world_model


def transition(identifier, duration=1.0):
    return {'action_id':identifier, 's':[0.2,0.1,0.0,1.0],
            'a':'simple','y':[duration,1.0,0.2]}


class AtomicT8CursorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runtime=SimpleNamespace(home=Path(self.tmp.name),store=object())

    def test_checkpoint_restart_does_not_double_train(self):
        rows=[transition('a'),transition('b')]
        with patch.object(world_model,'transitions',return_value=rows):
            first=OnlineWorld(self.runtime)
            self.assertEqual(first.update()['learned'],2)
            count=first.model.seen
            second=OnlineWorld(self.runtime)
            self.assertEqual(second.update()['learned'],0)
            self.assertEqual(second.model.seen,count)
            self.assertEqual(second.processed,['a','b'])

    def test_crash_before_checkpoint_replays_only_uncommitted_update(self):
        with patch.object(world_model,'transitions',return_value=[transition('a')]):
            first=OnlineWorld(self.runtime)
            self.assertEqual(first.update()['learned'],1)
        with patch.object(world_model,'transitions',return_value=[transition('a'),transition('b')]):
            second=OnlineWorld(self.runtime)
            with patch.object(second.model,'checkpoint',side_effect=RuntimeError('crash')):
                with self.assertRaisesRegex(RuntimeError,'crash'):
                    second.update()
            restarted=OnlineWorld(self.runtime)
            self.assertEqual(restarted.model.seen,1)
            self.assertEqual(restarted.update()['learned'],1)
            self.assertEqual(OnlineWorld(self.runtime).model.seen,2)

    def test_legacy_cursor_mismatch_refuses_unsafe_replay(self):
        with patch.object(world_model,'transitions',return_value=[transition('a')]):
            world=OnlineWorld(self.runtime)
            world.model.observe(*world.encode(transition('a')))
            world.model.checkpoint()  # legacy: no IDs, no cursor
        with self.assertRaisesRegex(ValueError,'no trusted T8 cursor'):
            OnlineWorld(self.runtime)

    def test_checkpoint_ids_follow_rollback_weights(self):
        with patch.object(world_model,'transitions',return_value=[transition('a')]):
            world=OnlineWorld(self.runtime)
            world.update()
        with patch.object(world_model,'transitions',return_value=[transition('a'),transition('b')]):
            world.update()
        world.model.rollback()
        self.assertEqual(world.model.processed_ids,['a'])
        self.assertEqual(world.model.seen,1)

    def test_reject_invalid_checkpoint_identifiers(self):
        world=OnlineWorld(self.runtime)
        with self.assertRaises(ValueError):
            world.model.checkpoint(processed_ids=['same','same'])
        self.assertFalse(world.model.path.exists())


if __name__=='__main__':
    unittest.main()
