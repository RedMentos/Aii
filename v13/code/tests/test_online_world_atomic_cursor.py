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

    def test_failed_checkpoint_restores_live_weights_before_same_process_retry(self):
        rows=[transition('a')]
        with patch.object(world_model,'transitions',return_value=rows):
            world=OnlineWorld(self.runtime)
            world.update()
            original_w=world.model.W.copy()
            original_seen=world.model.seen
            rows.append(transition('b'))
            checkpoint=world.model.checkpoint
            with patch.object(world.model,'checkpoint',side_effect=OSError('disk failure')):
                with self.assertRaisesRegex(OSError,'disk failure'):
                    world.update()
            np.testing.assert_array_equal(world.model.W,original_w)
            self.assertEqual(world.model.seen,original_seen)
            self.assertEqual(world.processed,['a'])
            self.assertEqual(world.update()['learned'],1)
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
        result=world.rollback()
        self.assertEqual(result['status'],'ROLLED_BACK_PERSISTED')
        self.assertEqual(world.processed,['a'])
        self.assertEqual(world.model.processed_ids,['a'])
        self.assertEqual(world.model.seen,1)
        restarted=OnlineWorld(self.runtime)
        self.assertEqual(restarted.processed,['a'])
        self.assertEqual(restarted.model.seen,1)
        with patch.object(world_model,'transitions',return_value=[transition('a'),transition('b')]):
            self.assertEqual(restarted.update()['learned'],1)
            self.assertEqual(OnlineWorld(self.runtime).model.seen,2)

    def test_failed_rollback_replace_preserves_active_checkpoint(self):
        with patch.object(world_model,'transitions',return_value=[transition('a'),transition('b')]):
            world=OnlineWorld(self.runtime)
            world.update()
        active=world.model.W.copy()
        with patch('v13.continuous_predictor.os.replace',side_effect=OSError('disk full')):
            with self.assertRaisesRegex(OSError,'disk full'):
                world.rollback()
        np.testing.assert_array_equal(world.model.W,active)
        np.testing.assert_array_equal(OnlineWorld(self.runtime).model.W,active)
        self.assertEqual(OnlineWorld(self.runtime).processed,['a','b'])

    def test_legacy_rollback_rejected_before_active_checkpoint_replacement(self):
        # A legacy prior snapshot lacks committed IDs, while the current
        # checkpoint has valid source-bound T8 IDs.
        world=OnlineWorld(self.runtime)
        world.model.checkpoint()  # prior legacy state with no cursor
        with patch.object(world_model,'transitions',return_value=[transition('a')]):
            world.update()
        active_bytes=world.model.path.read_bytes()
        active_weights=world.model.W.copy()
        active_ids=list(world.processed)
        with self.assertRaisesRegex(ValueError,'no trusted T8 cursor'):
            world.rollback()
        self.assertEqual(world.model.path.read_bytes(),active_bytes)
        np.testing.assert_array_equal(world.model.W,active_weights)
        self.assertEqual(world.processed,active_ids)
        self.assertEqual(OnlineWorld(self.runtime).processed,active_ids)

    def test_reject_invalid_checkpoint_identifiers(self):
        world=OnlineWorld(self.runtime)
        with self.assertRaises(ValueError):
            world.model.checkpoint(processed_ids=['same','same'])
        self.assertFalse(world.model.path.exists())


if __name__=='__main__':
    unittest.main()
