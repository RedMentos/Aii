"""Run37 native None-span sentinel versus malformed confidence regressions."""
from __future__ import annotations

import math
import unittest

from v13.agi import solver as original
from v13.agi.solver_confidence_finite_candidate import safe_confidence
from v13.agi.solver_confidence_null_sentinel_candidate import (
    safe_confidence_null_aware, REVISION,
)
from v13.focal import token_confidence


class Run37NullSentinel(unittest.TestCase):
    def test_real_native_token_confidence_no_answer_span_is_legitimate_none(self):
        tc = token_confidence([('{"summary":"ok"}', -0.1)], field="answer")
        self.assertIsNone(tc["field_min_prob"])
        self.assertIsNone(tc["field_mean_prob"])
        self.assertTrue(0 < tc["mean_prob"] <= 1)
        metrics = {"token_confidence": tc}
        self.assertEqual(safe_confidence(metrics), (0., "invalid:field_min_prob"))
        self.assertEqual(safe_confidence_null_aware(metrics),
                         (tc["mean_prob"], "mean_prob"))
        self.assertEqual(safe_confidence_null_aware(metrics),
                         original.confidence(metrics))

    def test_none_priority_skips_to_finite_next_key(self):
        cases = [
            ({"field_min_prob": None, "field_mean_prob": .75, "mean_prob": .9},
             (.75, "field_mean_prob")),
            ({"field_min_prob": None, "field_mean_prob": None, "mean_prob": .9},
             (.9, "mean_prob")),
            ({"field_min_prob": None, "field_mean_prob": None, "mean_prob": None},
             (.5, "none")),
            ({}, (.5, "none")),
        ]
        for tc, expected in cases:
            with self.subTest(tc=tc):
                self.assertEqual(safe_confidence_null_aware(
                    {"token_confidence": tc}), expected)

    def test_absent_token_confidence_none_is_not_malformed(self):
        for metrics in (None, {}, {"token_confidence": None},
                        {"duration_s": 1}, {"token_confidence": {}}):
            with self.subTest(metrics=metrics):
                self.assertEqual(safe_confidence_null_aware(metrics),
                                 (.5, "none"))

    def test_present_invalid_priority_remains_hard_zero(self):
        for invalid in (float("nan"), float("inf"), float("-inf"),
                        True, False, "0.95", [], 10**10000):
            with self.subTest(invalid=repr(invalid)[:60]):
                self.assertEqual(safe_confidence_null_aware({
                    "token_confidence": {
                        "field_min_prob": invalid, "field_mean_prob": .95,
                        "mean_prob": .99,
                    }}), (0., "invalid:field_min_prob"))
        self.assertEqual(safe_confidence_null_aware({
            "token_confidence": []}), (0., "invalid:token_confidence"))
        self.assertEqual(safe_confidence_null_aware("bad"),
                         (0., "invalid:metrics"))

    def test_valid_finite_original_parity(self):
        for v in (0., .1, .5, 1., -2., 2.):
            with self.subTest(v=v):
                m = {"token_confidence": {"field_min_prob": v}}
                self.assertEqual(safe_confidence_null_aware(m),
                                 original.confidence(m))
                self.assertEqual(safe_confidence_null_aware(m),
                                 safe_confidence(m))
        self.assertTrue(REVISION.startswith("run37-ag12-native-null-sentinel"))

    def test_same_outputs_null_sentinel_does_not_lose_valid_vote(self):
        tc = token_confidence([('{"summary":"ok"}', -0.1)], field="answer")
        m = {"token_confidence": tc}
        old = original.combine([
            {"role": "B1_DETAIL", "answer": "cat",
             "confidence": original.confidence(m)[0]},
            {"role": "B2_GIST", "answer": "dog", "confidence": .7},
        ])
        run31 = original.combine([
            {"role": "B1_DETAIL", "answer": "cat",
             "confidence": safe_confidence(m)[0]},
            {"role": "B2_GIST", "answer": "dog", "confidence": .7},
        ])
        run37 = original.combine([
            {"role": "B1_DETAIL", "answer": "cat",
             "confidence": safe_confidence_null_aware(m)[0]},
            {"role": "B2_GIST", "answer": "dog", "confidence": .7},
        ])
        self.assertEqual(old["answer"], "cat")
        self.assertEqual(run31["answer"], "dog")
        self.assertEqual(run37, old)


if __name__ == "__main__":
    unittest.main()
