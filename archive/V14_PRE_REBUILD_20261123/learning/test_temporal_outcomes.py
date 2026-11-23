import tempfile
import unittest
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
        result = self.store.resolve("x", at=11, observed=False, evidence="T8:verified-window", observation_complete=True)
        self.assertEqual(result["status"], "OMITTED")
        self.assertEqual(result["error"], -.8)
        self.assertEqual(TemporalOutcomes(self.path).learning_intent("x")["prediction_error"], -.8)

    def test_censored(self):
        self.add()
        self.assertIsNone(self.store.resolve("x", at=11, observed=False)["error"])
        self.assertIsNone(self.store.learning_intent("x"))

    def test_explicit_censored_event_closes_immediately_without_learning_signal(self):
        self.add()
        result = self.store.resolve("x", at=2, observed=False,
                                    evidence="T8:unknown-window", censored=True)
        self.assertEqual(result["status"], "CENSORED")
        self.assertIsNone(result["error"])
        self.assertIsNone(result["observed_outcome"])
        self.assertIsNone(self.store.learning_intent("x"))
        restored = TemporalOutcomes(self.path)
        self.assertEqual(restored.records["x"].status, "CENSORED")
        self.assertIsNone(restored.learning_intent("x"))

    def test_early_missing_then_late_observation(self):
        self.add()
        self.assertEqual(self.store.resolve("x", at=8, observed=False, evidence="T8:window", observation_complete=True)["status"], "PENDING")
        self.assertEqual(TemporalOutcomes(self.path).records["x"].status, "PENDING")
        late = self.store.resolve("x", at=11, observed=True, evidence="T8:late", observed_outcome="event")
        self.assertEqual(late["status"], "DELAYED")
        self.assertEqual(late["error"], -.8)

    def test_observed_match_is_positive_prediction_error(self):
        self.add()
        result = self.store.resolve("x", at=7, observed=True, evidence="T8:event", observed_outcome="event")
        self.assertEqual(result["status"], "OBSERVED")
        self.assertAlmostEqual(result["error"], .2)

    def test_observed_mismatch_is_negative_and_not_omission(self):
        self.add()
        result = self.store.resolve("x", at=7, observed=True, evidence="T8:wrong-event", observed_outcome="other")
        self.assertEqual(result["status"], "MISMATCHED")
        self.assertEqual(result["error"], -.8)
        self.assertEqual(self.store.learning_intent("x")["observed_outcome"], "other")

    def test_early_match_is_negative_prediction_error(self):
        self.add()
        result = self.store.resolve("x", at=2, observed=True, evidence="T8:early-event", observed_outcome="event")
        self.assertEqual(result["status"], "EARLY")
        self.assertEqual(result["error"], -.8)

    def test_bounds(self):
        self.add()
        with self.assertRaises(OverflowError): self.add("y")
        with self.assertRaises(ValueError): self.store.resolve("x", at=2, observed=True, evidence="T8:missing-outcome")
        result = self.store.resolve("x", at=7, observed=True, evidence="T8:ok", observed_outcome="event")
        self.assertEqual(result["status"], "OBSERVED")
        with self.assertRaises(ValueError): self.store.resolve("x", at=9, observed=True, evidence="T8:duplicate", observed_outcome="event")

    def test_failed_resolve_save_rolls_back_memory_and_disk(self):
        self.add(); before = self.path.read_bytes()
        with patch.object(self.store, "_save_unlocked", side_effect=OSError("disk full")):
            with self.assertRaises(OSError): self.store.resolve("x", at=11, observed=False, evidence="T8:window", observation_complete=True)
        self.assertEqual(self.store.records["x"].status, "PENDING")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(TemporalOutcomes(self.path).records["x"].status, "PENDING")

    def test_failed_expect_save_rolls_back_memory_and_disk(self):
        before = dict(self.store.records)
        with patch.object(self.store, "_save_unlocked", side_effect=OSError("disk full")):
            with self.assertRaises(OSError): self.add()
        self.assertEqual(self.store.records, before)
        self.assertFalse(self.path.exists())

    def test_invalid_numeric_and_boolean_inputs(self):
        with self.assertRaises(ValueError): TemporalOutcomes(self.path, max_pending=True)
        with self.assertRaises(ValueError): self.store.expect(Expectation("a", "T8:s", "WORLD", "event", 0, 1, 2, True))
        with self.assertRaises(ValueError): self.store.expect(Expectation(id="b", source="T8:s", owner="WORLD", outcome="event", opened_at=True, earliest=1, deadline=2, probability=.5))
        with self.assertRaises(ValueError): self.store.resolve("missing", at=True, observed=False)

    def test_invalid(self):
        with self.assertRaises(ValueError): self.store.expect(Expectation("a", "", "WORLD", "event", 0, 1, 2, .5))
        with self.assertRaises(ValueError): self.store.expect(Expectation("a", "T8", "WORLD", "event", 0, 1, 2, 1.2))


if __name__ == "__main__": unittest.main()
