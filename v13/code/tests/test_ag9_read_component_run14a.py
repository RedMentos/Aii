"""Run14A: AG9 read-side invalid component containment, software-only."""
from __future__ import annotations

import copy
import unittest

from v13.agi.metacog import Metacognition


class MemoryStore:
    def __init__(self):
        self.data = {}
        self.version = 0
        self.writes = 0

    def state(self, key, default):
        return copy.deepcopy(self.data.get(key, default)), self.version

    def set_state(self, key, state, expected=None):
        if expected != self.version:
            raise ValueError("STATE_VERSION_CHANGED")
        self.data[key] = copy.deepcopy(state)
        self.version += 1
        self.writes += 1


class AG9ReadComponentContainment(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.ag9 = Metacognition(self.store)

    def test_invalid_component_abstains_without_exception_or_retry(self):
        invalid = [None, True, False, [], {}, "", " ", "bad\nkey", "x" * 65]
        for component in invalid:
            with self.subTest(component=repr(component)):
                before = (self.store.version, self.store.writes)
                self.assertIsNone(self.ag9.calibrated(component, 0.6))
                self.assertEqual(self.ag9.decide(component, 0.6), {
                    "calibrated": None,
                    "second_attempt": False,
                    "abstain": True,
                    "reason": "INVALID_COMPONENT",
                })
                self.assertEqual((self.store.version, self.store.writes), before)

    def test_invalid_component_precedes_invalid_confidence(self):
        self.assertEqual(self.ag9.decide([], float("nan"))["reason"],
                         "INVALID_COMPONENT")
        self.assertEqual(self.ag9.decide("C3_LANGUAGE", float("nan")), {
            "calibrated": None, "second_attempt": False,
            "abstain": True, "reason": "INVALID_CONFIDENCE",
        })
        self.assertEqual(self.store.writes, 0)

    def test_valid_unknown_still_requests_second_attempt(self):
        self.assertEqual(self.ag9.decide("C3_LANGUAGE", 0.6), {
            "calibrated": None, "second_attempt": True,
            "abstain": False, "reason": "UNCALIBRATED",
        })
        self.assertIsNone(self.ag9.calibrated("C3_LANGUAGE", 0.6))

    def test_valid_supported_component_unchanged(self):
        for i in range(20):
            self.ag9.record("C3_LANGUAGE", i / 19, bool(i >= 10))
        before = self.store.writes
        value = self.ag9.calibrated("C3_LANGUAGE", 0.8)
        self.assertIsInstance(value, float)
        self.assertEqual(self.ag9.decide("C3_LANGUAGE", 0.8)["reason"],
                         "CALIBRATED")
        self.assertEqual(self.store.writes, before)


if __name__ == "__main__":
    unittest.main()
