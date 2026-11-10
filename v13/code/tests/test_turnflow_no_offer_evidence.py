"""NO_OFFER is a non-observation, not evidence of late B1/B2 overlap."""
import copy
import unittest

from v13 import turnflow


class MemoryStore:
    def __init__(self):
        self.value = None
        self.version = 0

    def state(self, key, default):
        return copy.deepcopy(self.value) if self.value is not None else default, self.version

    def set_state(self, key, value, expected):
        if expected != self.version:
            raise ValueError("version mismatch")
        self.value = copy.deepcopy(value)
        self.version += 1


class NoOfferEvidenceTests(unittest.TestCase):
    def test_no_offer_is_not_late_training_or_confirmed_overlap(self):
        store = MemoryStore()
        turnflow.plan(store, "event-no-offer", {}, 0, "B1_DETAIL")
        self.assertEqual(turnflow.observe(store, "event-no-offer", "NO_OFFER"), "NO_OFFER")
        report = turnflow.report(store)
        self.assertEqual(report["events_with_confirmed_overlap"], 0)
        self.assertEqual(report["actual_observer_outcomes"]["NO_OFFER"], 1)
        self.assertEqual(report["feedback_patterns"], {})
        with self.assertRaises(ValueError):
            turnflow.feedback(store, "event-no-offer", "wasteful")

    def test_real_late_observer_remains_timing_evidence(self):
        store = MemoryStore()
        turnflow.plan(store, "event-late", {}, 0, "B2_GIST")
        self.assertEqual(turnflow.observe(store, "event-late", "AFTER_OUTPUT"), "AFTER_OUTPUT")
        report = turnflow.report(store)
        self.assertEqual(report["events_with_confirmed_overlap"], 1)
        pattern = next(iter(report["feedback_patterns"].values()))
        self.assertEqual(pattern["too_late"], 1)
        self.assertEqual(turnflow.feedback(store, "event-late", "wasteful")["n"], 1)


if __name__ == "__main__":
    unittest.main()
