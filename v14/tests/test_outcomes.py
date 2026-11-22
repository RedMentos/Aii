"""Synthetic Linux tests; not Android or pretrained weight evidence."""
import tempfile
import unittest
from pathlib import Path
from v14.code.outcomes import OutcomeTracker

class OutcomeTests(unittest.TestCase):
    def test_coverage_and_restart(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "outcomes.db"
            now = [100.]
            a = OutcomeTracker(path, lambda: now[0])
            a.expect("a", "WORLD", "cue:1", "reward", .8, 110)
            self.assertEqual(a.settle("a").status, "PENDING")
            a.close()
            now[0] = 111
            b = OutcomeTracker(path, lambda: now[0])
            self.assertEqual(b.settle("a").status, "CENSORED")
            self.assertIsNone(b.settle("a").error)
            b.expect("b", "SELF", "cue:2", "reward", .8, 120)
            now[0] = 121
            self.assertEqual(b.settle("b", window_complete=True, source_ref="window:1").error, -.8)
            self.assertIsNone(b.settle("b").error)
            b.close()

    def test_positive_source_and_invalid_probability(self):
        with tempfile.TemporaryDirectory() as td:
            a = OutcomeTracker(Path(td) / "outcomes.db", lambda: 100.)
            a.expect("a", "B1", "cue", "reward", .3, 101)
            with self.assertRaises(ValueError):
                a.settle("a", observed=True)
            self.assertAlmostEqual(a.settle("a", observed=True, source_ref="sensor:1").error, .7)
            with self.assertRaises(ValueError):
                a.expect("bad", "B2", "cue", "reward", float("nan"), 101)
            a.close()

if __name__ == "__main__":
    unittest.main()
