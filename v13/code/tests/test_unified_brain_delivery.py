"""Real coordinator + source-bound B1/B2 Offers -> one shared C3 report.

Native calls are replaced by role-specific deterministic generators; this proves
routing, provenance and delivery, NOT Android timing, neural understanding or
real learned B3/JEF bridge quality.
"""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock

from v13.common import Limits
from v13.operator import Operator
from v13.runtime import Runtime


QUESTION = (
    "Compare details with planning. The rent is 120 euros. "
    "The plan preserves a long-term reserve."
)


class RoleRunner:
    def __init__(self, role, calls, *, fail_b1=False):
        self.role = role
        self.calls = calls
        self.fail_b1 = fail_b1
        self.last_metrics = {"status": "FINAL", "role": role, "synthetic": True}

    def generate(self, messages, cancel, deadline, *args, **kwargs):
        self.calls.append((self.role, messages))
        if self.role == "B1_DETAIL" and self.fail_b1:
            self.last_metrics = {"status": "DEADLINE", "role": self.role,
                                 "synthetic": True}
            raise Limits("Synthetic B1 observation timed out")
        if self.role == "B1_DETAIL":
            offer = {
                "summary": "The exact rent is 120 euros.",
                "quotes": ["The rent is 120 euros."],
                "uncertainty": "low",
                "needs_reentry": False,
            }
        elif self.role == "B2_GIST":
            offer = {
                "summary": "Planning needs a long-term reserve.",
                "quotes": ["The plan preserves a long-term reserve."],
                "uncertainty": "low",
                "needs_reentry": False,
            }
        else:
            yield "One combined response."
            return
        yield json.dumps(offer, ensure_ascii=False)


class CrossOrganDelivery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.cfg.update(
            deadline_seconds=90,
            observer_mode="background",
            observer_schedule="A_THEN_B_SEQUENTIAL",
            b2_quote_select="off",
            offer_quote_context_chars=0,
            b2_state_slots=0,
        )
        Operator(self.r).run(":effort max")
        self.r._route = Mock(return_value=("both", {"source": "TEST_BOTH"}))
        self.r.learner.output_delta = Mock(return_value=None)
        self.calls = []
        self.runners = {}

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def execute(self, *, fail_b1=False):
        def get(role):
            if role not in self.runners:
                self.runners[role] = RoleRunner(role, self.calls, fail_b1=fail_b1)
            return self.runners[role]
        self.r.pool.get = Mock(side_effect=get)
        event_id = Operator(self.r).run(QUESTION)
        until = time.monotonic() + 12
        while not self.r.idle() and time.monotonic() < until:
            time.sleep(.01)
        self.assertTrue(self.r.idle(), "turn stalled")
        rows = self.r.store.rows(
            "SELECT * FROM messages WHERE event_id=? AND role='assistant'", (event_id,))
        self.assertEqual(len(rows), 1, "one authorized outward message per event")
        self.assertEqual(rows[0]["status"], "FINAL", rows[0]["metadata"])
        self.assertEqual(rows[0]["text"], "One combined response.")
        c3_calls = [msgs for role, msgs in self.calls if role == "C3_LANGUAGE"]
        self.assertEqual(len(c3_calls), 1)
        meta = json.loads(rows[0]["metadata"])
        return event_id, meta, json.dumps(c3_calls[0], ensure_ascii=False)

    def test_two_real_source_bound_offers_are_consumed_by_one_report(self):
        event_id, meta, context = self.execute()
        self.assertIn("B1_DETAIL", [role for role, _ in self.calls])
        self.assertIn("B2_GIST", [role for role, _ in self.calls])
        self.assertIn("C3_LANGUAGE", [role for role, _ in self.calls])
        self.assertIn("B1_DETAIL", context)
        self.assertIn("B2_GIST", context)
        self.assertIn("The rent is 120 euros.", context)
        self.assertIn("The plan preserves a long-term reserve.", context)
        self.assertEqual(len(meta["selected_offer_ids"]), 2)
        self.assertEqual(meta["action_selection"] is not None, True)
        stored = self.r.store.rows(
            "SELECT payload FROM packets WHERE kind='OfferPacket' AND event_id=?", (event_id,))
        self.assertEqual(len(stored), 2)

    def test_failing_b1_never_fabricates_an_offer_and_b2_still_reaches_c3(self):
        event_id, meta, context = self.execute(fail_b1=True)
        self.assertIn("B1_DETAIL", [role for role, _ in self.calls])
        self.assertIn("B2_GIST", context)
        self.assertNotIn("The exact rent is 120 euros.", context)
        self.assertEqual(len(meta["selected_offer_ids"]), 1)
        stored = self.r.store.rows(
            "SELECT payload FROM packets WHERE kind='OfferPacket' AND event_id=?", (event_id,))
        self.assertEqual(len(stored), 1)
        self.assertEqual(json.loads(stored[0]["payload"])["role"], "B2_GIST")


if __name__ == "__main__":
    unittest.main()
