"""Run595: explicit source-bound ContextPlan selection for multi-organ feedback."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from v13.runtime import Runtime
from v13.operator import Operator
from v13 import context_os as C


LONG = "Prior garden/weather conversation with several details. " * 8


class ContextPlanSelector(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.ctx = C.ContextOS(self.r.store, self.r.cfg)
        self.op = Operator(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self, query="query"):
        return self.r.store.event(self.r.session, query)["event_id"]

    def plan(self, eid, role="C3_LANGUAGE", history=None):
        return self.ctx.plan(eid, role, "SYS", [], history or [], "query")

    def history(self):
        out = []
        for i in range(10):
            out += [{"event_id": f"old{i}", "role": "user", "text": "Q " + LONG},
                    {"event_id": f"old{i}", "role": "assistant", "text": "A " + LONG}]
        return out

    def test_multiple_roles_require_explicit_packet_and_credit_only_selected_decisions(self):
        eid = self.event()
        detail = self.plan(eid, "B1_DETAIL", self.history())
        gist = self.plan(eid, "C3_LANGUAGE")
        self.assertTrue(any(x.startswith("compress") for x in detail["plan"]["decisions"]))
        before = self.ctx._load()[0]["policy"]
        with self.assertRaisesRegex(ValueError, "Mehrere ContextPlans"):
            self.ctx.outcome(eid, 0.)
        self.assertEqual(self.ctx._load()[0]["policy"], before)
        self.assertEqual(self.ctx.outcome(eid, 0., plan_id=gist["packet_id"]), {})
        self.assertEqual(self.ctx._load()[0]["policy"], before)
        self.assertIn("compress", self.ctx.outcome(eid, 0., plan_id=detail["packet_id"]))

    def test_same_role_reentry_is_still_ambiguous(self):
        eid = self.event()
        a = self.plan(eid)
        b = self.plan(eid)
        self.assertNotEqual(a["packet_id"], b["packet_id"])
        with self.assertRaisesRegex(ValueError, "Mehrere ContextPlans"):
            self.ctx.outcome(eid, .5)
        self.assertEqual(self.ctx.outcome(eid, .5, plan_id=a["packet_id"]), {})

    def test_wrong_event_or_unknown_packet_id_refused(self):
        a, b = self.event("first"), self.event("second")
        pa = self.plan(a)
        self.plan(b)
        with self.assertRaisesRegex(ValueError, "gehört nicht"):
            self.ctx.outcome(b, .5, plan_id=pa["packet_id"])
        with self.assertRaisesRegex(ValueError, "gehört nicht"):
            self.ctx.outcome(a, .5, plan_id="pkt_missing")

    def test_orphan_packet_never_substituted_for_valid_packet(self):
        eid = self.event()
        with mock.patch.object(self.r.store, "set_state", side_effect=ValueError("CAS fail")):
            with self.assertRaisesRegex(ValueError, "CAS fail"):
                self.plan(eid)
        orphan = self.r.store.one(
            "SELECT id FROM packets WHERE kind='ContextPlan' AND event_id=?", (eid,))["id"]
        valid = self.plan(eid)
        with self.assertRaisesRegex(ValueError, "Mehrere ContextPlans"):
            self.ctx.outcome(eid, .5)
        with self.assertRaisesRegex(ValueError, "not committed"):
            self.ctx.outcome(eid, .5, plan_id=orphan)
        self.assertEqual(self.ctx.outcome(eid, .5, plan_id=valid["packet_id"]), {})

    def test_tampered_selected_packet_fails_and_plans_mark_uncommitted(self):
        eid = self.event()
        plan = self.plan(eid)
        pid = plan["packet_id"]
        row = self.r.store.one("SELECT payload FROM packets WHERE id=?", (pid,))
        p = json.loads(row["payload"])
        p["decisions"] = ["restore"]
        with self.r.store.tx() as db:
            db.execute("UPDATE packets SET payload=? WHERE id=?", (json.dumps(p), pid))
        self.assertEqual(self.ctx.plans(eid)[0]["committed"], False)
        with self.assertRaisesRegex(ValueError, "digest changed"):
            self.ctx.outcome(eid, .5, plan_id=pid)

    def test_generation_row_tamper_refused(self):
        eid = self.event()
        plan = self.plan(eid)
        with self.r.store.tx() as db:
            db.execute("UPDATE packets SET generation_id=? WHERE id=?",
                       ("gen_tampered", plan["packet_id"]))
        with self.assertRaisesRegex(ValueError, "generation mismatch"):
            self.ctx.outcome(eid, .5, plan_id=plan["packet_id"])

    def test_operator_selector_and_one_plan_restart_compatibility(self):
        eid = self.event()
        p = self.plan(eid)
        listing = json.loads(self.op.run(":ctxos plans " + eid))
        self.assertEqual(len(listing), 1)
        self.assertEqual(listing[0]["packet_id"], p["packet_id"])
        self.assertTrue(listing[0]["committed"])
        self.r.close()
        self.r = Runtime(self.home)
        self.ctx = C.ContextOS(self.r.store, self.r.cfg)
        self.op = Operator(self.r)
        self.assertEqual(json.loads(self.op.run(":ctxos outcome " + eid + " 0.5")), {})
        self.assertEqual(json.loads(self.op.run(":ctxos outcome " + eid + " 0.5 " + p["packet_id"])), {})


if __name__ == "__main__":
    unittest.main()
