"""Negative control: C5 currently counts repeated observations of one event.

Review-only test; it deliberately documents the existing unsafe behavior.
It is NOT an acceptance test for activating C5.
"""
import copy
import unittest
from v13.actionlearn import C5Learning, MIN_N

class MemoryState:
    def __init__(self):
        self.value = None
        self.version = 0
    def state(self, key, default=None):
        return copy.deepcopy(self.value), self.version
    def set_state(self, key, value, expected=None):
        if expected != self.version:
            raise ValueError("conflict")
        self.value = copy.deepcopy(value)
        self.version += 1

class RepeatedCreditNegativeControl(unittest.TestCase):
    def test_one_event_can_reach_minimum_sample_count(self):
        store = MemoryState()
        c5 = C5Learning(store)
        # Same event, same human signal; a delivery retry must not be
        # interpreted as three independent observations.
        for _ in range(MIN_N):
            c5.learn("simple|low", "C3_LANGUAGE",
                     event_id="single-event", human_approval=1.)
        row = c5.report()["actions"]["simple|low|C3_LANGUAGE"]
        self.assertEqual(row["n"], MIN_N)
        self.assertGreater(row["promote"], 0.)
        self.assertEqual(row["modulators"]["human_approval"], 1.)

    def test_correction_does_not_retract_earlier_credit(self):
        store = MemoryState()
        c5 = C5Learning(store)
        c5.learn("simple|low", "C3_LANGUAGE",
                 event_id="same-event", human_approval=1.)
        c5.learn("simple|low", "C3_LANGUAGE",
                 event_id="same-event", human_correction=1.)
        row = c5.report()["actions"]["simple|low|C3_LANGUAGE"]
        self.assertEqual(row["n"], 2)
        self.assertEqual(row["modulators"]["human_approval"], 1.)
        self.assertEqual(row["modulators"]["human_correction"], 1.)

if __name__ == "__main__":
    unittest.main()
