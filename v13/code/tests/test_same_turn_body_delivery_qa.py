"""QA regression: a nontrivial same-turn B1+B2 wake must reach the C4 path.

The current recovery policy is allowed to protect C3, but it must not silently
turn BOTH pre-answer body offers into post-commit-only work on the same turn.
This is intentionally red against the current Core candidate until its budget
policy preserves a measured same-turn body window.
"""
import json
import threading
import time
import unittest

from v13.cognition import Cognition
from v13.common import Limits


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


class SameTurnBodyDeliveryTests(unittest.TestCase):
    def test_nontrivial_both_body_wake_reaches_preanswer_generation_boundary(self):
        class Store:
            def __init__(self):
                self.attempted = []
                self.deferred = []
                self.assert_bounded_query = False
                self.current_role = None

            def rows(self, query, args):
                self.assert_bounded_query = (
                    "SELECT status,metadata" in query and
                    "LIMIT ?" in query and args == (6,)
                )
                return [_c3_failure(), _c3_failure()]

            def log(self, kind, event_id, metrics):
                if kind == "native_body_deferred_for_c3":
                    self.deferred.append((metrics.get("role"), metrics.get("status")))

            def read_source(self, ref):
                self.attempted.append(self.current_role)
                raise BodyAttemptReached("body reached source/generation boundary")

        class Runtime:
            def __init__(self, store):
                self.store = store
                self.cfg = {
                    "deadline_seconds": 30,
                    "observer_mode": "background",
                    "b2_control": "two_body",
                }
                self.cancel_event = threading.Event()
                self.session = "qa-same-turn"

        store = Store()
        cognition = Cognition(Runtime(store))
        valid_until = time.monotonic() + 30
        deadline = valid_until - 10
        event = {
            "event_id": "qa-nontrivial-both",
            "brain_generation_id": "qa-generation",
            "source_ref": {
                "sha256": "a" * 64,
                "char_start": 0,
                "char_end": 120,
            },
        }
        attempted = []
        deferred = []
        for role in ("B1_DETAIL", "B2_GIST"):
            store.current_role = role
            try:
                cognition.offer(
                    role, event, version=0, deadline=deadline,
                    valid_until=valid_until,
                )
            except BodyAttemptReached:
                attempted.append(role)
            except Limits:
                deferred.append(role)

        self.assertTrue(store.assert_bounded_query)
        self.assertEqual(
            attempted, ["B1_DETAIL", "B2_GIST"],
            "both same-turn body roles were silently deferred before C4; "
            f"attempted={attempted}, deferred={deferred}, log={store.deferred}",
        )
        self.assertEqual(deferred, [])


if __name__ == "__main__":
    unittest.main()
