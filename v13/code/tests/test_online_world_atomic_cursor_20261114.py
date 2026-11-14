"""Synthetic crash/restart regression for predictor-bound trusted T8 cursor."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from v13.online_world import OnlineWorld
from v13 import world_model

class AtomicT8CursorTests(unittest.TestCase):
    def row(self, key):
        return {'action_id':key,'s':[0.1,0.2,0.3,0.4],
                'y':[0.2,0.1,0.3],'a':world_model.ACTIONS[0]}

    def test_restart_does_not_retrain_when_legacy_cursor_is_stale(self):
        with tempfile.TemporaryDirectory() as td:
            runtime=SimpleNamespace(home=td,store=object())
            rows=[self.row('trusted-a')]
            with patch('v13.online_world.world_model.transitions',return_value=rows):
                first=OnlineWorld(runtime)
                self.assertEqual(first.update()['learned'],1)
                seen=first.model.seen
                # A stale legacy cursor cannot override the atomic checkpoint.
                (Path(td)/'online_world'/'cursor.json').write_text(
                    '{"revision":"v13-online-world-v1","processed":[]}')
                second=OnlineWorld(runtime)
                self.assertEqual(second.update()['learned'],0)
                self.assertEqual(second.model.seen,seen)
                np.testing.assert_array_equal(second.model.W,first.model.W)

    def test_checkpoint_failure_does_not_publish_cursor(self):
        with tempfile.TemporaryDirectory() as td:
            runtime=SimpleNamespace(home=td,store=object())
            rows=[self.row('trusted-a')]
            with patch('v13.online_world.world_model.transitions',return_value=rows):
                first=OnlineWorld(runtime)
                first.update()
                with patch.object(first.model,'checkpoint',side_effect=OSError('disk full')):
                    with patch('v13.online_world.world_model.transitions',
                               return_value=rows+[self.row('trusted-b')]):
                        with self.assertRaises(OSError):first.update()
                restarted=OnlineWorld(runtime)
                self.assertEqual(restarted.model.seen,1)
                self.assertEqual(restarted.processed,['trusted-a'])
                with patch('v13.online_world.world_model.transitions',
                           return_value=rows+[self.row('trusted-b')]):
                    self.assertEqual(restarted.update()['learned'],1)
                    self.assertEqual(OnlineWorld(runtime).model.seen,2)

    def test_retry_same_process_after_failed_checkpoint_is_exactly_once(self):
        with tempfile.TemporaryDirectory() as td:
            runtime=SimpleNamespace(home=td,store=object())
            rows=[self.row('trusted-a')]
            with patch('v13.online_world.world_model.transitions',return_value=rows):
                learner=OnlineWorld(runtime)
                learner.update()
                baseline=learner.model.seen
                with patch.object(learner.model,'checkpoint',side_effect=OSError('disk full')):
                    with patch('v13.online_world.world_model.transitions',
                               return_value=rows+[self.row('trusted-b')]):
                        with self.assertRaises(OSError):learner.update()
                self.assertEqual(learner.model.seen,baseline)
                self.assertEqual(learner.processed,['trusted-a'])
                with patch('v13.online_world.world_model.transitions',
                           return_value=rows+[self.row('trusted-b')]):
                    self.assertEqual(learner.update()['learned'],1)
                self.assertEqual(learner.model.seen,baseline+1)
                np.testing.assert_array_equal(learner.model.W,OnlineWorld(runtime).model.W)

if __name__=='__main__':
    unittest.main()
