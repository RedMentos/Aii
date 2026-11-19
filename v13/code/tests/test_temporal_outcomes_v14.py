"""Synthetic-only V14 temporal outcome tests; no Android or weight proof."""
import unittest
from v13.temporal_outcomes import Expectation, TemporalOutcomeTracker

class Bus:
    def __init__(self): self.calls = []
    def publish(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return {"status": "PUBLISHED"}

class TemporalTests(unittest.TestCase):
    def setUp(self):
        self.tracker = TemporalOutcomeTracker(capacity=1)
        self.record = Expectation("one", "source:1", "food", 100, 200, .8)
        self.tracker.expect(self.record)

    def test_observed(self):
        r = self.tracker.resolve("one", 150, observed="food")
        self.assertEqual(r["status"], "OBSERVED")
        self.assertAlmostEqual(r["prediction_error"], .2)
        self.assertFalse(r["weight_update_authorized"])

    def test_omission_requires_complete_observation(self):
        r = self.tracker.resolve("one", 201, observation_complete=True)
        self.assertEqual(r["status"], "OMITTED")
        self.assertAlmostEqual(r["prediction_error"], -.8)

    def test_missing_observation_is_censored(self):
        r = self.tracker.resolve("one", 201)
        self.assertEqual(r["status"], "CENSORED")
        self.assertIsNone(r["prediction_error"])

    def test_early_omission_is_pending(self):
        self.assertEqual(self.tracker.resolve("one", 199, observation_complete=True)["status"], "PENDING")

    def test_delayed_and_different(self):
        self.assertEqual(self.tracker.resolve("one", 250, observed="food")["status"], "DELAYED")
        t = TemporalOutcomeTracker()
        t.expect(self.record)
        self.assertEqual(t.resolve("one", 150, observed="water")["status"], "DIFFERENT")

    def test_cancelled(self):
        self.assertEqual(self.tracker.resolve("one", 150, cancelled=True)["status"], "CANCELLED")

    def test_enlightened_consumer_contract(self):
        self.tracker.resolve("one", 201, observation_complete=True)
        bus = Bus()
        self.tracker.emit_feedback("one", {"event_id":"e","brain_generation_id":"g"}, bus)
        self.assertEqual(bus.calls[0][0][1:3], ("OUTCOME", "FEEDBACK"))
        self.assertEqual(bus.calls[0][1]["authority"], "CONTROL_ONLY")

    def test_duplicate_and_capacity(self):
        with self.assertRaises(ValueError): self.tracker.expect(self.record)
        with self.assertRaises(OverflowError):
            self.tracker.expect(Expectation("two","source:2","food",0,1,.5))

    def test_invalid_probabilities(self):
        for probability in (-.1, 1.1, float("nan")):
            with self.assertRaises(ValueError):
                Expectation("x","source","food",0,1,probability)

    def test_idempotent_terminal(self):
        a = self.tracker.resolve("one", 201, observation_complete=True)
        self.assertEqual(a, self.tracker.resolve("one", 300, observed="food"))

if __name__ == "__main__":
    unittest.main()
