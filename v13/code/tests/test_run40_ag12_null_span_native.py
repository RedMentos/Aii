"""Run40 mock native null-span subtype and three-path vote invariants."""
from __future__ import annotations

import json
import unittest

from v13.agi.solver_confidence_null_span_native_candidate import (
    TripleConfidenceBodySolver, native_field_min_type, REVISION,
)


class Runner:
    def __init__(self, answer, metrics):
        self.answer, self.last_metrics = answer, metrics
        self.calls = 0
    def generate(self, messages, cancel, deadline, **kwargs):
        self.calls += 1
        yield json.dumps({"answer": self.answer})


class Pool:
    def __init__(self, members):
        self.members = members
    def get(self, role):
        return self.members[role]


def sample(roles, expected="cat"):
    views = [{"id": "id" + str(i), "prompt": "synthetic secret choice"}
             for i in range(88)]
    suite = {"items": [{"id": v["id"], "answer": expected} for v in views]}
    solver = TripleConfidenceBodySolver(Pool(roles), tuple(roles), seed=19)
    results = solver.batch(views)
    scored = [{"id": v["id"],
               "correct": int(results[v["id"]]["answer"] == expected),
               "confidence": results[v["id"]]["confidence"]}
              for v in views]
    return solver, suite, scored


class Run40NativeSubtype(unittest.TestCase):
    def test_native_primary_subtype_classification(self):
        cases = [
            (None, "metrics_absent"),
            ("bad", "metrics_malformed"),
            ({}, "token_confidence_absent"),
            ({"token_confidence": None}, "token_confidence_none"),
            ({"token_confidence": []}, "token_confidence_malformed"),
            ({"token_confidence": {}}, "field_min_absent"),
            ({"token_confidence": {"field_min_prob": None}}, "field_min_none_span"),
            ({"token_confidence": {"field_min_prob": .75}}, "field_min_finite"),
            ({"token_confidence": {"field_min_prob": float("nan")}}, "field_min_nonfinite"),
            ({"token_confidence": {"field_min_prob": float("inf")}}, "field_min_nonfinite"),
            ({"token_confidence": {"field_min_prob": True}}, "field_min_boolean"),
            ({"token_confidence": {"field_min_prob": "0.75"}}, "field_min_other_malformed"),
            ({"token_confidence": {"field_min_prob": 10**400}}, "field_min_numeric_overflow"),
        ]
        for metrics, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(native_field_min_type(metrics), expected)

    def test_none_span_recovers_legacy_vote_with_same_native_outputs(self):
        roles = {
            "B1_DETAIL": Runner("cat", {"token_confidence": {
                "field_min_prob": None, "field_mean_prob": None, "mean_prob": .9}}),
            "B2_GIST": Runner("dog", {"token_confidence": {"field_min_prob": .7}}),
            "C3_LANGUAGE": Runner("", {"token_confidence": {"field_min_prob": .1}}),
        }
        s, suite, scored = sample(roles)
        agg = s.aggregate(suite, scored)
        self.assertEqual(agg["role_calls"], 264)
        self.assertEqual(agg["legacy_comparable_rows"], 88)
        self.assertEqual(agg["correct"]["legacy_comparable"], 88)
        self.assertEqual(agg["correct"]["finite_all"], 0)
        self.assertEqual(agg["correct"]["null_all"], 88)
        self.assertEqual(agg["changed_votes"]["finite_null_all"], 88)
        self.assertEqual(agg["changed_votes"]["legacy_null_comparable"], 0)
        self.assertEqual(agg["by_role"]["B1_DETAIL"]["native_field_min_types"],
                         {"field_min_none_span": 88})
        self.assertEqual(agg["by_role"]["B1_DETAIL"]["finite_source_counts"],
                         {"invalid:field_min_prob": 88})
        self.assertEqual(agg["by_role"]["B1_DETAIL"]["null_source_counts"],
                         {"mean_prob": 88})
        self.assertEqual([r.calls for r in roles.values()], [88, 88, 88])
        self.assertEqual(s._rows, {})
        self.assertNotIn("synthetic secret choice", json.dumps(agg))
        self.assertNotIn('"cat"', json.dumps(agg))
        self.assertNotIn('"dog"', json.dumps(agg))
        self.assertTrue(REVISION.startswith("run40-ag12-null-span"))

    def test_real_nonfinite_remains_hard_zero_for_both_finite_paths(self):
        roles = {
            "B1_DETAIL": Runner("cat", {"token_confidence": {
                "field_min_prob": float("nan"), "field_mean_prob": .99}}),
            "B2_GIST": Runner("dog", {"token_confidence": {"field_min_prob": .7}}),
        }
        s, suite, scored = sample(roles, expected="dog")
        agg = s.aggregate(suite, scored)
        self.assertEqual(agg["correct"]["finite_all"], 88)
        self.assertEqual(agg["correct"]["null_all"], 88)
        self.assertEqual(agg["changed_votes"]["finite_null_all"], 0)
        self.assertEqual(agg["by_role"]["B1_DETAIL"]["native_field_min_types"],
                         {"field_min_nonfinite": 88})

    def test_legacy_overflow_stays_incomparable(self):
        roles = {
            "B1_DETAIL": Runner("cat", {"token_confidence": {
                "field_min_prob": 10**400}}),
            "B2_GIST": Runner("dog", {"token_confidence": {"field_min_prob": .7}}),
        }
        s, suite, scored = sample(roles, expected="dog")
        agg = s.aggregate(suite, scored)
        self.assertEqual(agg["legacy_comparable_rows"], 0)
        self.assertEqual(agg["legacy_incomparable_rows"], 88)
        self.assertEqual(agg["by_role"]["B1_DETAIL"]["legacy_errors"], 88)
        self.assertEqual(agg["by_role"]["B1_DETAIL"]["native_field_min_types"],
                         {"field_min_numeric_overflow": 88})

    def test_scored_null_vote_mismatch_fails_closed(self):
        roles = {"B1_DETAIL": Runner("cat", {"token_confidence": {
            "field_min_prob": .7}})}
        s, suite, scored = sample(roles)
        scored[0]["correct"] = 0
        with self.assertRaisesRegex(ValueError, "RUN40_NULL_VOTE_SCORE_MISMATCH"):
            s.aggregate(suite, scored)

    def test_incomplete_role_and_duplicate_identity_fail_closed(self):
        roles = {"B1_DETAIL": Runner("cat", {"token_confidence": {
            "field_min_prob": .7}})}
        s, suite, scored = sample(roles)
        del s._rows[("B1_DETAIL", "id4")]
        with self.assertRaisesRegex(ValueError, "RUN40_ROLE_CALL_INCOMPLETE"):
            s.aggregate(suite, scored)
        s2 = TripleConfidenceBodySolver(Pool(roles), ("B1_DETAIL",), seed=19)
        view = {"id": "duplicate", "prompt": "synthetic"}
        s2.ask("B1_DETAIL", view)
        with self.assertRaisesRegex(ValueError, "RUN40_DUPLICATE_ROLE_ITEM"):
            s2.ask("B1_DETAIL", view)


if __name__ == "__main__":
    unittest.main()
