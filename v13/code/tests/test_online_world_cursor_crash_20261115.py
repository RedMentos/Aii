"""Crash-boundary regression for online-world checkpoint/cursor alignment."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from v13.online_world import OnlineWorld


class CursorCrashBoundaryTest(unittest.TestCase):
    def test_checkpoint_ahead_of_cursor_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = SimpleNamespace(home=root, store=object())
            world = OnlineWorld(runtime)
            x, action, y = world.encode({'s': [0., 0., 0., 0.], 'y': [1., 0., 0.], 'a': 'simple'})
            world.model.observe(x, action, y)
            world.model.checkpoint()
            # Simulates power loss after the numeric update is durable but
            # before the cursor is published. No duplicate training allowed.
            with self.assertRaisesRegex(ValueError, 'without online world cursor'):
                OnlineWorld(runtime)

    def test_cursor_checkpoint_generation_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = SimpleNamespace(home=root, store=object())
            world = OnlineWorld(runtime)
            world.model.checkpoint()
            world.cursor.write_text(json.dumps({
                'revision': 'v13-online-world-v1',
                'processed': [],
                'predictor_seen': 1,
            }))
            with self.assertRaisesRegex(ValueError, 'checkpoint/cursor mismatch'):
                OnlineWorld(runtime)

    def test_clean_empty_restart(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = SimpleNamespace(home=root, store=object())
            world = OnlineWorld(runtime)
            self.assertEqual(OnlineWorld(runtime).model.seen, 0)


if __name__ == '__main__':
    unittest.main()
