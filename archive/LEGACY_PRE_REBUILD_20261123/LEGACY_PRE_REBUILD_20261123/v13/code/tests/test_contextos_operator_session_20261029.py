"""N7 operator last/outcome must not read or learn from another chat."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13.operator import Operator
from v13 import context_os as C


class ContextOSOperatorSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        self.c = C.controller(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def plan(self, session, marker):
        e = self.r.store.event(session, marker)
        self.c.plan(e["event_id"], "C3_LANGUAGE", "SYS", [], [], marker)
        return e["event_id"]

    def test_last_is_current_session_only_even_when_foreign_is_newer(self):
        own = self.plan(self.r.session, "CURRENT_CONTEXT_PLAN_MARKER")
        other = self.r.store.new_session()
        foreign = self.plan(other, "FOREIGN_CONTEXT_PLAN_MARKER")
        self.assertNotEqual(own, foreign)
        got = json.loads(self.op.run(":ctxos last"))
        self.assertEqual(got["event_id"], own)
        self.assertNotEqual(got["event_id"], foreign)
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")
        self.assertEqual(self.r.pool.pids(), [])

    def test_only_foreign_plan_returns_null_not_cross_session_payload(self):
        other = self.r.store.new_session()
        self.plan(other, "FOREIGN_ONLY_CONTEXT_PLAN")
        self.assertIsNone(json.loads(self.op.run(":ctxos last")))

    def test_foreign_or_unknown_outcome_refused_before_learning(self):
        other = self.r.store.new_session()
        foreign = self.plan(other, "FOREIGN_OUTCOME_MARKER")
        before = self.r.store.state(C.KEY)
        with patch.object(C.ContextOS, "outcome",
                          side_effect=AssertionError("cross-session feedback")):
            for eid in (foreign, "missing-context-event"):
                with self.subTest(eid=eid), self.assertRaisesRegex(
                        ValueError, "aktuellen Chat"):
                    self.op.run(":ctxos outcome " + eid + " 0.8")
        self.assertEqual(self.r.store.state(C.KEY), before)

    def test_current_session_outcome_remains_explicitly_usable(self):
        own = self.plan(self.r.session, "CURRENT_OUTCOME_MARKER")
        got = json.loads(self.op.run(":ctxos outcome " + own + " 0.8"))
        self.assertIsInstance(got, dict)
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")


if __name__ == "__main__":
    unittest.main()
