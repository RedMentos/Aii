"""Regression: an interrupted model/cursor two-file commit must fail closed."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from v13 import world_model
from v13.online_world import OnlineWorld, REVISION


class OnlineWorldCursorRecovery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runtime = SimpleNamespace(home=Path(self.temp.name), store=object())

    def _one_observation(self, obj):
        obj.model.observe(np.zeros(7), 0, np.ones(7))
        obj.model.checkpoint()

    def test_fresh_empty_model_has_no_cursor(self):
        obj = OnlineWorld(self.runtime)
        self.assertEqual(obj.model.seen, 0)
        self.assertEqual(obj.processed, [])
        self.assertEqual(OnlineWorld(self.runtime).model.seen, 0)

    def test_crash_after_predictor_checkpoint_before_cursor_fails_closed(self):
        obj = OnlineWorld(self.runtime)
        self._one_observation(obj)
        with self.assertRaisesRegex(ValueError, "checkpoint/cursor mismatch"):
            OnlineWorld(self.runtime)

    def test_cursor_ahead_of_model_fails_closed(self):
        obj = OnlineWorld(self.runtime)
        obj.cursor.write_text(json.dumps({"revision": REVISION, "processed": ["action-a"]}))
        with self.assertRaisesRegex(ValueError, "checkpoint/cursor mismatch"):
            OnlineWorld(self.runtime)

    def test_consistent_model_and_cursor_restore(self):
        obj = OnlineWorld(self.runtime)
        self._one_observation(obj)
        obj.cursor.write_text(json.dumps({"revision": REVISION, "processed": ["action-a"]}))
        restored = OnlineWorld(self.runtime)
        self.assertEqual(restored.model.seen, 1)
        self.assertEqual(restored.processed, ["action-a"])
        with patch.object(world_model, "transitions", return_value=[]):
            result = restored.update()
        self.assertEqual(result["learned"], 0)

    def test_duplicate_cursor_identifiers_fail_closed(self):
        obj = OnlineWorld(self.runtime)
        for _ in range(2):
            self._one_observation(obj)
        obj.cursor.write_text(json.dumps({"revision": REVISION, "processed": ["same", "same"]}))
        with self.assertRaisesRegex(ValueError, "checkpoint/cursor mismatch"):
            OnlineWorld(self.runtime)


if __name__ == "__main__":
    unittest.main()
