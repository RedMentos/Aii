"""Run31 original RED witness and isolated finite token confidence candidate tests."""
from __future__ import annotations

import math
import unittest

from v13.agi import solver as original
from v13.agi.solver_confidence_finite_candidate import safe_confidence, REVISION


def metrics(value, key="field_min_prob"):
    return {"token_confidence": {key: value}}


class PoisonedEquality:
    def __eq__(self, other):
        raise AssertionError("untrusted __eq__ must not run")


class Run31FiniteConfidence(unittest.TestCase):
    def test_original_bug_witness_is_not_silently_rewritten(self):
        # A test of historical source behavior, not a native-run observation.
        self.assertEqual(original.confidence(metrics(float("nan")))[0], 1.0)
        self.assertEqual(original.confidence(metrics(float("inf")))[0], 1.0)

    def test_candidate_nonfinite_and_boolean_are_not_certainty(self):
        for v in (float("nan"), float("inf"), float("-inf"),
                  True, False, 10**10000):
            with self.subTest(value=str(v)[:20]):
                self.assertEqual(safe_confidence(metrics(v)),
                                 (0.0, "invalid:field_min_prob"))

    def test_invalid_primary_does_not_fallback_to_secondary(self):
        for v in (float("nan"), "0.9", None, True):
            with self.subTest(value=repr(v)):
                self.assertEqual(safe_confidence({"token_confidence": {
                    "field_min_prob": v, "field_mean_prob": 0.95}}),
                    (0.0, "invalid:field_min_prob"))

    def test_valid_finite_priority_and_clip_preserved(self):
        for v, expected in ((0, 0.), (0.6, 0.6), (1., 1.),
                            (-2., 0.), (2., 1.)):
            with self.subTest(value=v):
                self.assertEqual(safe_confidence(metrics(v)),
                                 (expected, "field_min_prob"))
        self.assertEqual(safe_confidence({"token_confidence": {
            "field_mean_prob": .3, "mean_prob": .9}}),
            (.3, "field_mean_prob"))
        self.assertEqual(safe_confidence(metrics(.75, "mean_prob")),
                         (.75, "mean_prob"))

    def test_missing_is_distinct_from_malformed(self):
        for v in (None, {}, {"other": 2}, {"token_confidence": {}}):
            self.assertEqual(safe_confidence(v), (.5, "none"))
        for v in ("", [], True, PoisonedEquality(),
                  {"token_confidence": None},
                  {"token_confidence": []}):
            result = safe_confidence(v)
            self.assertEqual(result[0], 0.)
            self.assertTrue(result[1].startswith("invalid:"))

    def test_candidate_is_deterministic_and_input_unchanged(self):
        m = {"token_confidence": {"field_min_prob": .4, "mean_prob": .9}}
        before = repr(m)
        for _ in range(5):
            self.assertEqual(safe_confidence(m), (.4, "field_min_prob"))
        self.assertEqual(repr(m), before)
        self.assertTrue(REVISION.startswith("run31-ag12-finite"))


if __name__ == "__main__":
    unittest.main()
