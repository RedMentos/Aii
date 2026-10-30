"""Run33 synthetic/mock regression for isolated AG12 finite-confidence vote path."""
from __future__ import annotations

import json
import math
import threading
import time
import unittest

from v13.agi import solver as original
from v13.agi.solver_confidence_finite_vote_candidate import (
    FiniteConfidenceBodySolver, REVISION,
)


class FakeRunner:
    def __init__(self, answer, metrics, fail=False):
        self.answer = answer
        self.last_metrics = metrics
        self.fail = fail
        self.calls = []

    def generate(self, messages, cancel, deadline, **kwargs):
        self.calls.append((messages, cancel, deadline, kwargs))
        if self.fail:
            raise RuntimeError("synthetic runner failure")
        yield json.dumps({"answer": self.answer})


class FakePool:
    def __init__(self, runners):
        self.runners = runners
        self.calls = []

    def get(self, role):
        self.calls.append(role)
        return self.runners[role]


def metric(value, key="field_min_prob"):
    return {"token_confidence": {key: value}}


def solver(cls, runners):
    pool = FakePool(runners)
    return cls(pool, tuple(runners), item_seconds=30, seed=13), pool


class Run33FiniteVoteShadow(unittest.TestCase):
    def test_valid_single_role_exact_output_and_generation_parity(self):
        for value in (0., 0.15, 1., -2., 2.):
            with self.subTest(value=value):
                a, pa = solver(original.BodySolver, {"B1_DETAIL": FakeRunner("cat", metric(value))})
                b, pb = solver(FiniteConfidenceBodySolver, {"B1_DETAIL": FakeRunner("cat", metric(value))})
                view = {"id": "synthetic1", "prompt": "Choose a label"}
                self.assertEqual(a.ask("B1_DETAIL", view), b.ask("B1_DETAIL", view))
                self.assertEqual(pa.calls, ["B1_DETAIL"])
                self.assertEqual(pb.calls, ["B1_DETAIL"])
                old = pa.runners["B1_DETAIL"].calls[0]
                new = pb.runners["B1_DETAIL"].calls[0]
                self.assertEqual(old[0], new[0])
                self.assertEqual(old[3], new[3])
                self.assertIsInstance(new[1], threading.Event)
                self.assertTrue(time.monotonic() < new[2] <= time.monotonic() + 31)

    def test_valid_multi_role_batch_vote_parity(self):
        def runners():
            return {
                "B1_DETAIL": FakeRunner("cat", metric(.6)),
                "B2_GIST": FakeRunner("dog", metric(.8)),
                "C3_LANGUAGE": FakeRunner("cat", metric(.5, "mean_prob")),
            }
        a, _ = solver(original.BodySolver, runners())
        b, _ = solver(FiniteConfidenceBodySolver, runners())
        views = [{"id": "synthetic1", "prompt": "Choose a label"}]
        self.assertEqual(a.batch(views), b.batch(views))
        self.assertEqual(a.stats.keys(), b.stats.keys())
        self.assertEqual(b.batch(views)["synthetic1"]["answer"], "cat")

    def test_malformed_primary_no_longer_outvotes_valid_member(self):
        for poisoned in (float("nan"), float("inf"), True, "0.95"):
            with self.subTest(value=repr(poisoned)):
                def runners():
                    return {
                        "B1_DETAIL": FakeRunner("cat", {"token_confidence": {
                            "field_min_prob": poisoned, "field_mean_prob": .99}}),
                        "B2_GIST": FakeRunner("dog", metric(.7)),
                    }
                a, _ = solver(original.BodySolver, runners())
                b, _ = solver(FiniteConfidenceBodySolver, runners())
                view = [{"id": "synthetic1", "prompt": "Choose a label"}]
                old = a.batch(view)["synthetic1"]
                new = b.batch(view)["synthetic1"]
                if isinstance(poisoned, str):
                    # Historical solver skips a string primary and falls back to .99.
                    self.assertEqual(old["answer"], "cat")
                else:
                    self.assertEqual(old["answer"], "cat")
                self.assertEqual(new["answer"], "dog")
                self.assertEqual(new["voters"], 2)
                self.assertEqual(new["confidence"], .35)

    def test_invalid_confidence_source_and_missing_default(self):
        cases = [
            (metric(float("nan")), (0., "invalid:field_min_prob")),
            (metric(float("-inf")), (0., "invalid:field_min_prob")),
            (metric(True), (0., "invalid:field_min_prob")),
            ({"token_confidence": {"field_min_prob": None, "mean_prob": .99}},
             (0., "invalid:field_min_prob")),
            ({}, (.5, "none")),
            ({"token_confidence": {"field_mean_prob": .4}}, (.4, "field_mean_prob")),
        ]
        for metrics, expected in cases:
            with self.subTest(metrics=repr(metrics)):
                s, _ = solver(FiniteConfidenceBodySolver, {"B1_DETAIL": FakeRunner("cat", metrics)})
                row = s.ask("B1_DETAIL", {"prompt": "Choose a label"})
                self.assertEqual((row["confidence"], row["confidence_source"]), expected)

    def test_original_class_unmodified_and_failure_behavior_preserved(self):
        self.assertTrue(REVISION.startswith("run33-ag12-finite-vote-shadow"))
        self.assertEqual(original.confidence(metric(float("nan")))[0], 1.)
        for cls in (original.BodySolver, FiniteConfidenceBodySolver):
            s, _ = solver(cls, {"B1_DETAIL": FakeRunner("cat", metric(.7), fail=True)})
            with self.assertRaises(original.Unavailable):
                s.batch([{"id": "synthetic1", "prompt": "Choose a label"}])
            self.assertEqual(s.stopped, "ERROR")
            cancel = threading.Event()
            cancel.set()
            s2, p2 = solver(cls, {"B1_DETAIL": FakeRunner("cat", metric(.7))})
            self.assertEqual(s2.batch([{"id": "synthetic1", "prompt": "x"}], cancel=cancel), {})
            self.assertEqual(p2.calls, [])

    def test_explicit_deadline_and_cancellation_identity_preserved(self):
        cancel = threading.Event()
        deadline = time.monotonic() + 2
        s, pool = solver(FiniteConfidenceBodySolver,
                         {"B1_DETAIL": FakeRunner("cat", metric(.5))})
        s.ask("B1_DETAIL", {"prompt": "x"}, cancel=cancel, deadline=deadline)
        messages, observed_cancel, observed_deadline, kwargs = pool.runners["B1_DETAIL"].calls[0]
        self.assertIs(observed_cancel, cancel)
        self.assertEqual(observed_deadline, deadline)
        self.assertEqual(kwargs["max_tokens"], 40)
        self.assertEqual(kwargs["confidence_field"], "answer")
        self.assertEqual(kwargs["seed"], 13)
        self.assertEqual(messages[1], {"role": "user", "content": "x"})


if __name__ == "__main__":
    unittest.main()
