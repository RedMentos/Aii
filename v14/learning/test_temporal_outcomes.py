import tempfile, unittest
from unittest.mock import patch
from pathlib import Path
from temporal_outcomes import TemporalOutcomes, Expectation

class TemporalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "outcomes.json"
        self.store = TemporalOutcomes(self.path, max_pending=1)
    def tearDown(self): self.tmp.cleanup()
    def add(self, id="x"):
        self.store.expect(Expectation(id, "T8:source", "WORLD", "event", 0, 5, 10, .8))
    def test_omission_restart(self):
        self.add()
        self.assertEqual(self.store.resolve("x", at=11, observed=False, evidence="T8:verified-window", observation_complete=True)["error"], -.8)
        self.assertEqual(TemporalOutcomes(self.path).learning_intent("x")["prediction_error"], -.8)
    def test_censored(self):
        self.add()
        self.assertIsNone(self.store.resolve("x", at=11, observed=False)["error"])
        self.assertIsNone(self.store.learning_intent("x"))
    def test_early_missing(self):
        self.add()
        self.assertEqual(self.store.resolve("x", at=8, observed=False, evidence="T8:window", observation_complete=True)["status"], "PENDING")
        self.assertEqual(TemporalOutcomes(self.path).records["x"].status, "PENDING")
        self.assertEqual(self.store.resolve("x", at=11, observed=True, evidence="T8:late")["status"], "DELAYED")
    def test_delayed(self):
        self.add()
        self.assertEqual(self.store.resolve("x", at=12, observed=True, evidence="T8:event")["status"], "DELAYED")
        self.assertAlmostEqual(self.store.learning_intent("x")["prediction_error"], .2)
    def test_bounds(self):
        self.add()
        with self.assertRaises(OverflowError): self.add("y")
        with self.assertRaises(ValueError): self.store.resolve("x", at=2, observed=True)
        self.assertEqual(self.store.resolve("x", at=7, observed=True, evidence="T8:ok")["status"], "OBSERVED")
        with self.assertRaises(ValueError): self.store.resolve("x", at=9, observed=True, evidence="T8:duplicate")
    def test_failed_resolve_save_rolls_back_memory_and_disk(self):
        self.add()
        before = self.path.read_bytes()
        with patch.object(self.store, "save", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.store.resolve("x", at=11, observed=False, evidence="T8:window", observation_complete=True)
        self.assertEqual(self.store.records["x"].status, "PENDING")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(TemporalOutcomes(self.path).records["x"].status, "PENDING")

    def test_failed_expect_save_rolls_back_memory_and_disk(self):
        before = dict(self.store.records)
        with patch.object(self.store, "save", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.add()
        self.assertEqual(self.store.records, before)
        self.assertFalse(self.path.exists())

    def test_invalid(self):
        with self.assertRaises(ValueError): self.store.expect(Expectation("a", "", "WORLD", "event", 0, 1, 2, .5))
        with self.assertRaises(ValueError): self.store.expect(Expectation("a", "T8", "WORLD", "event", 0, 1, 2, 1.2))
if __name__ == "__main__": unittest.main()
