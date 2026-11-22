"""Run36 mock same-output native-confidence incidence and aggregate-only controls."""
from __future__ import annotations

import json
import threading
import unittest

from v13.agi import solver as original
from v13.agi.solver_confidence_native_incidence_candidate import (
    PairedConfidenceBodySolver, REVISION,
)


class Runner:
    def __init__(self, answer, metrics):
        self.answer = answer
        self.last_metrics = metrics
        self.calls = 0

    def generate(self, messages, cancel, deadline, **kwargs):
        self.calls += 1
        yield json.dumps({"answer": self.answer})


class Pool:
    def __init__(self, members):
        self.members = members

    def get(self, role):
        return self.members[role]


def sample(roles, expected="dog"):
    views = [{"id": "id" + str(i), "prompt": "synthetic choice"}
             for i in range(88)]
    suite = {"items": [{"id": v["id"], "answer": expected} for v in views]}
    s = PairedConfidenceBodySolver(Pool(roles), tuple(roles), seed=17)
    results = s.batch(views)
    scored = [{"id": v["id"],
               "correct": int(results[v["id"]]["answer"] == expected),
               "confidence": results[v["id"]]["confidence"]}
              for v in views]
    return s, suite, scored


class Run36ConfidenceIncidence(unittest.TestCase):
    def test_invalid_native_metric_changes_vote_without_second_generation(self):
        roles = {
            "B1_DETAIL": Runner("cat", {"token_confidence": {
                "field_min_prob": float("nan"), "field_mean_prob": .99}}),
            "B2_GIST": Runner("dog", {"token_confidence": {"field_min_prob": .7}}),
            "C3_LANGUAGE": Runner("", {"token_confidence": {"field_min_prob": .1}}),
        }
        s, suite, scored = sample(roles)
        agg = s.aggregate(suite, scored)
        self.assertEqual(agg["role_calls"], 264)
        self.assertEqual(agg["legacy_comparable_rows"], 88)
        self.assertEqual(agg["legacy_correct_on_comparable"], 0)
        self.assertEqual(agg["finite_correct_on_comparable"], 88)
        self.assertEqual(agg["same_output_changed_votes"], 88)
        self.assertEqual(agg["by_role"]["B1_DETAIL"]["invalid_present"], 88)
        self.assertEqual([r.calls for r in roles.values()], [88, 88, 88])
        self.assertEqual(s._rows, {})
        self.assertNotIn("synthetic choice", json.dumps(agg))
        self.assertNotIn('"cat"', json.dumps(agg))
        self.assertNotIn('"dog"', json.dumps(agg))

    def test_valid_confidence_keeps_same_output_vote(self):
        roles = {
            "B1_DETAIL": Runner("cat", {"token_confidence": {"field_min_prob": .8}}),
            "B2_GIST": Runner("dog", {"token_confidence": {"field_min_prob": .3}}),
        }
        s, suite, scored = sample(roles, expected="cat")
        agg = s.aggregate(suite, scored)
        self.assertEqual(agg["same_output_changed_votes"], 0)
        self.assertEqual(agg["legacy_correct_on_comparable"], 88)
        self.assertEqual(agg["finite_correct_all"], 88)
        self.assertEqual(agg["by_role"]["B1_DETAIL"]["invalid_present"], 0)
        self.assertTrue(REVISION.startswith("run36-ag12-native-confidence"))

    def test_legacy_overflow_marked_incomparable_not_hidden(self):
        roles = {
            "B1_DETAIL": Runner("cat", {"token_confidence": {
                "field_min_prob": 10**10000}}),
            "B2_GIST": Runner("dog", {"token_confidence": {"field_min_prob": .7}}),
        }
        s, suite, scored = sample(roles)
        agg = s.aggregate(suite, scored)
        self.assertEqual(agg["legacy_incomparable_rows"], 88)
        self.assertEqual(agg["legacy_comparable_rows"], 0)
        self.assertEqual(agg["by_role"]["B1_DETAIL"]["legacy_errors"], 88)
        self.assertEqual(agg["finite_correct_all"], 88)

    def test_scored_row_mismatch_fails_closed(self):
        roles = {"B1_DETAIL": Runner("dog", {"token_confidence": {
            "field_min_prob": .7}})}
        s, suite, scored = sample(roles)
        scored[0]["correct"] = 0
        with self.assertRaisesRegex(ValueError, "RUN36_FINITE_VOTE_SCORE_MISMATCH"):
            s.aggregate(suite, scored)

    def test_incomplete_role_and_duplicate_identity_fail_closed(self):
        roles = {"B1_DETAIL": Runner("dog", {"token_confidence": {
            "field_min_prob": .7}})}
        s, suite, scored = sample(roles)
        del s._rows[("B1_DETAIL", "id4")]
        with self.assertRaisesRegex(ValueError, "RUN36_ROLE_CALL_INCOMPLETE"):
            s.aggregate(suite, scored)
        s2 = PairedConfidenceBodySolver(Pool(roles), ("B1_DETAIL",), seed=17)
        view = {"id": "duplicate", "prompt": "synthetic"}
        s2.ask("B1_DETAIL", view)
        with self.assertRaisesRegex(ValueError, "RUN36_DUPLICATE_ROLE_ITEM"):
            s2.ask("B1_DETAIL", view)

    def test_original_solver_unchanged_and_cancelled(self):
        self.assertEqual(original.confidence({"token_confidence": {
            "field_min_prob": float("nan")}})[0], 1.)
        s = PairedConfidenceBodySolver(Pool({"B1_DETAIL": Runner("dog", {})}),
                                       ("B1_DETAIL",), seed=17)
        cancel = threading.Event()
        cancel.set()
        self.assertEqual(s.batch([{"id": "one", "prompt": "x"}], cancel=cancel), {})
        self.assertEqual(s._rows, {})


if __name__ == "__main__":
    unittest.main()
