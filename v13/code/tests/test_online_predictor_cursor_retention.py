"""Regression: routine checkpoints must not silently erase the trusted T8 cursor."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from v13.continuous_predictor import OnlinePredictor

class CursorRetentionTests(unittest.TestCase):
    def test_routine_checkpoint_retains_cursor_across_restart(self):
        with tempfile.TemporaryDirectory() as root:
            p=OnlinePredictor(2,2,root,seed=11,replay=8)
            p.observe(np.array([0.1,0.2]),0,np.array([0.2,0.3]),rehearsals=0)
            p.checkpoint(processed_ids=["trusted:t8:1"])
            p.observe(np.array([0.3,0.4]),1,np.array([0.4,0.5]),rehearsals=0)
            p.checkpoint()
            q=OnlinePredictor(2,2,root,seed=99,replay=8)
            self.assertEqual(q.checkpoint_ids,["trusted:t8:1"])
            self.assertEqual(q.seen,2)

    def test_stream_checkpoint_preserves_cursor(self):
        with tempfile.TemporaryDirectory() as root:
            p=OnlinePredictor(2,2,root,replay=8)
            p.checkpoint(processed_ids=["trusted:t8:1"])
            p.learn_stream([(np.array([0.1,0.2]),0,np.array([0.2,0.1]))],checkpoint_every=1)
            q=OnlinePredictor(2,2,root,replay=8)
            self.assertEqual(q.checkpoint_ids,["trusted:t8:1"])

    def test_explicit_none_clears_cursor(self):
        with tempfile.TemporaryDirectory() as root:
            p=OnlinePredictor(2,2,root,replay=8)
            p.checkpoint(processed_ids=["trusted:t8:1"])
            p.checkpoint(processed_ids=None)
            self.assertIsNone(OnlinePredictor(2,2,root,replay=8).checkpoint_ids)

if __name__=="__main__":
    unittest.main()
