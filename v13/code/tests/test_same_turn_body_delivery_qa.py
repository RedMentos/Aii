"""QA: same-turn body admission in source and staged budget profiles.

The source recovery policy keeps its 26 s C3 reserve. The integrated staged
candidate deliberately uses the 45% pre-answer window (16.5 s on a 30 s turn)
and a 1 s minimum role slice. The same test runs against both compositions.
Synthetic clock, Store and model boundaries are not native model or Redmi
performance evidence.
"""
import json
import threading
import time
import unittest
from unittest.mock import patch

from v13 import observer_schedule as obs
from v13.cognition import Cognition
from v13.common import Limits


def _expected_c3_reserve_seconds():
    """Select the explicit source or staged contract; reject unknown profiles."""
    from v13 import native_turn_budget

    if hasattr(native_turn_budget, "NATIVE_FIRST_RESERVE_FRACTION"):
        return 26.0
    if hasattr(native_turn_budget, "MIN_ROLE_SLICE_S"):
        return 16.5
    raise AssertionError("unrecognized native turn-budget profile")


class BodyAttemptReached(Exception):
    pass


def _c3_failure():
    return {
        "status": "DEADLINE",
        "metadata": json.dumps({
            "runner": {
                "role": "C3_LANGUAGE",
                "generated_tokens": 0,
                "last_phase": "prefill",
                "duration_s": 29.1,
            },
        }),
    }


class _Store:
    def __init__(self):
        self.logs = []
        self.attempted = []
        self.current_role = None
        self.bounded_query = False

    def rows(self, query, args):
        self.bounded_query = (
            "SELECT status,metadata" in query
            and "LIMIT ?" in query
            and args == (6,)
        )
        return [_c3_failure(), _c3_failure()]

    def log(self, kind, event_id, metrics):
        self.logs.append((kind, event_id, dict(metrics)))

    def read_source(self, source_ref):
        self.attempted.append(self.current_role)
        raise BodyAttemptReached("source/generation boundary reached")


class _Runtime:
    def __init__(self, store):
        self.store = store
        self.cfg = {
            "deadline_seconds": 30,
            "observer_mode": "background",
            "b2_control": "two_body",
        }
        self.cancel_event = threading.Event()
        self.session = "qa-fair-budget"


def _event():
    return {
        "event_id": "qa-fair-budget-event",
        "brain_generation_id": "qa-fair-budget-generation",
        "source_ref": {
            "sha256": "a" * 64,
            "char_start": 0,
            "char_end": 120,
        },
    }


class SameTurnAdmissionTests(unittest.TestCase):
    def test_both_roles_reach_source_boundary_with_distinct_fair_recovery_deadlines(self):
        store = _Store()
        cognition = Cognition(_Runtime(store))
        event = _event()
        start = time.monotonic()
        valid_until = start + 30.0
        role_deadlines = {
            "B1_DETAIL": start + 2.0,
            "B2_GIST": start + 4.0,
        }
        now = [start]
        attempted = []
        deferred = []

        # Mirror the sequential observer: the first body consumes its own
        # 2-second slice, then the peer receives the remaining 2 seconds.
        with patch("v13.cognition.time.monotonic", side_effect=lambda: now[0]):
            for role in ("B1_DETAIL", "B2_GIST"):
                store.current_role = role
                try:
                    cognition.offer(
                        role, event, version=0,
                        deadline=role_deadlines[role],
                        valid_until=valid_until,
                    )
                except BodyAttemptReached:
                    attempted.append(role)
                except Limits:
                    deferred.append(role)
                now[0] = role_deadlines[role]

        self.assertTrue(store.bounded_query)
        self.assertEqual(attempted, ["B1_DETAIL", "B2_GIST"])
        self.assertEqual(deferred, [])
        budget_rows = [metrics for kind, _, metrics in store.logs
                       if kind == "native_body_budgeted_for_c3"]
        self.assertEqual(len(budget_rows), 2)
        by_role = {row["role"]: row for row in budget_rows}
        self.assertEqual(set(by_role), {"B1_DETAIL", "B2_GIST"})
        self.assertGreater(by_role["B1_DETAIL"]["preanswer_seconds_available"], 1.9)
        self.assertLessEqual(by_role["B1_DETAIL"]["preanswer_seconds_available"], 2.0)
        self.assertGreater(by_role["B2_GIST"]["preanswer_seconds_available"], 1.9)
        self.assertLessEqual(by_role["B2_GIST"]["preanswer_seconds_available"], 2.0)
        self.assertTrue(all(row["status"] == "PREANSWER_BUDGETED" for row in budget_rows))
        expected_reserve = _expected_c3_reserve_seconds()
        self.assertTrue(all(abs(row["c3_reserved_seconds"] - expected_reserve) < 0.01
                            for row in budget_rows))
        self.assertTrue(all(row["recent_real_prefill_failures"] == 2
                            for row in budget_rows))

    def test_sub_one_second_slice_defers_only_that_role(self):
        store = _Store()
        cognition = Cognition(_Runtime(store))
        event = _event()
        start = time.monotonic()
        valid_until = start + 30.0

        store.current_role = "B1_DETAIL"
        with self.assertRaises(Limits):
            cognition.offer(
                "B1_DETAIL", event, version=0,
                deadline=start + 0.5,
                valid_until=valid_until,
            )

        store.current_role = "B2_GIST"
        with self.assertRaises(BodyAttemptReached):
            cognition.offer(
                "B2_GIST", event, version=0,
                deadline=start + 4.0,
                valid_until=valid_until,
            )

        self.assertTrue(store.bounded_query)
        self.assertEqual(store.attempted, ["B2_GIST"])
        deferred = [metrics for kind, _, metrics in store.logs
                    if kind == "native_body_deferred_for_c3"]
        budgeted = [metrics for kind, _, metrics in store.logs
                    if kind == "native_body_budgeted_for_c3"]
        self.assertEqual(len(deferred), 1)
        self.assertEqual(deferred[0]["role"], "B1_DETAIL")
        self.assertEqual(deferred[0]["status"], "POSTCOMMIT_ELIGIBLE")
        self.assertLess(deferred[0]["preanswer_seconds_available"], 1.0)
        self.assertAlmostEqual(
            deferred[0]["c3_reserved_seconds"], _expected_c3_reserve_seconds(), places=2,
        )
        self.assertEqual(deferred[0]["recent_real_prefill_failures"], 2)
        self.assertEqual(len(budgeted), 1)
        self.assertEqual(budgeted[0]["role"], "B2_GIST")
        self.assertEqual(budgeted[0]["status"], "PREANSWER_BUDGETED")


class NinetySecondFairShareTests(unittest.TestCase):
    def test_90s_40_5s_window_splits_20_25s_in_both_sequential_orders(self):
        observer_end = 40.5  # 45% of the 90-second turn
        per_body_cap = 35.0  # current configured observer_seconds
        cases = (
            (obs.DEFAULT, ["B1_DETAIL", "B2_GIST"]),
            ("B_THEN_A_SEQUENTIAL", ["B2_GIST", "B1_DETAIL"]),
        )

        for schedule, expected_roles in cases:
            with self.subTest(schedule=schedule):
                now = [0.0]
                seen = []

                def ask(role, use_peer, role_end=None):
                    self.assertTrue(use_peer)
                    self.assertIsNotNone(role_end)
                    native_end = min(observer_end, now[0] + per_body_cap, role_end)
                    seen.append((role, now[0], native_end, role_end))
                    now[0] = native_end
                    return role

                plan = obs.plan(schedule, ["B1_DETAIL", "B2_GIST"], "qa-90s")
                offers = obs.run(
                    plan, ask, observer_end, lambda role, exc: self.fail(
                        f"{role} rejected unexpectedly: {exc}"
                    ),
                    clock=lambda: now[0], budgeted=True,
                )

                self.assertEqual(offers, expected_roles)
                self.assertEqual([row[0] for row in seen], expected_roles)
                self.assertEqual(len(seen), 2)
                for _, started, native_end, role_end in seen:
                    self.assertAlmostEqual(native_end - started, 20.25, places=2)
                    self.assertAlmostEqual(role_end - started, 20.25, places=2)
                    self.assertLessEqual(native_end - started, per_body_cap)
                self.assertAlmostEqual(seen[-1][2], observer_end, places=2)


if __name__ == "__main__":
    unittest.main()
