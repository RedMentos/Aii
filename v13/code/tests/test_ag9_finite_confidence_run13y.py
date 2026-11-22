"""Run13Y test-first AG9 confidence/label integrity, in-memory StateBox."""
from __future__ import annotations

import copy
import math
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


class Ag9InputIntegrity(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.ag9 = Metacognition(self.store)

    def test_nonfinite_or_boolean_confidence_never_mutates_calibration(self):
        for value in (float("nan"), float("inf"), float("-inf"), True, False,
                      "NaN", "Infinity"):
            with self.subTest(value=str(value)):
                before = self.store.writes
                with self.assertRaises(ValueError):
                    self.ag9.record("C3_LANGUAGE", value, True)
                self.assertEqual(self.store.writes, before)
        self.assertIsNone(self.ag9.age_metric("C3_LANGUAGE"))

    def test_nonbinary_labels_never_become_positive_outcomes(self):
        for value in ("false", "true", "0", 0.0, 1.0, 2, -1, None, []):
            with self.subTest(value=str(value)):
                before = self.store.writes
                with self.assertRaises(ValueError):
                    self.ag9.record("B1_DETAIL", 0.75, value)
                self.assertEqual(self.store.writes, before)

    def test_invalid_component_cannot_create_state_key(self):
        for component in ("", "  ", None, True, "bad\nkey", "x" * 200):
            with self.subTest(component=str(component)):
                with self.assertRaises(ValueError):
                    self.ag9.record(component, 0.6, True)
        self.assertEqual(self.store.writes, 0)

    def test_invalid_confidence_decision_abstains_without_retry(self):
        for value in (float("nan"), float("inf"), float("-inf"), True,
                      "NaN", "Infinity", object()):
            with self.subTest(value=str(value)):
                self.assertEqual(self.ag9.decide("C3_LANGUAGE", value), {
                    "calibrated": None, "second_attempt": False,
                    "abstain": True, "reason": "INVALID_CONFIDENCE"})
                self.assertIsNone(self.ag9.calibrated("C3_LANGUAGE", value))
        self.assertEqual(self.store.writes, 0)

    def test_valid_binary_labels_and_finite_confidence_still_calibrate(self):
        for i in range(20):
            self.ag9.record("C3_LANGUAGE", i / 19, bool(i >= 10))
        self.assertEqual(self.store.writes, 20)
        self.assertEqual(self.ag9.report("C3_LANGUAGE")["components"]["C3_LANGUAGE"]["n"], 20)
        table = self.ag9.box.load()[0]["components"]["C3_LANGUAGE"]["calibrator"]
        self.assertEqual(len(table), 10)
        self.assertTrue(all(math.isfinite(x) and 0 <= x <= 1 for x in table))
        self.assertEqual(table, sorted(table))
        result = self.ag9.decide("C3_LANGUAGE", 0.8)
        self.assertEqual(result["reason"], "CALIBRATED")
        self.assertIsInstance(result["calibrated"], float)
        self.assertIsNotNone(self.ag9.age_metric("C3_LANGUAGE"))

    def test_finite_out_of_range_values_preserve_existing_clamp(self):
        for value in (-2, 2, 0.5, "0.5"):
            self.ag9.record("JEF", value, 1)
        pairs = self.ag9.box.load()[0]["components"]["JEF"]["pairs"]
        self.assertEqual(pairs, [[0.0, 1], [1.0, 1], [0.5, 1], [0.5, 1]])


if __name__ == "__main__":
    unittest.main()
