"""Run590: ContextPlan feedback requires an actual committed CAS receipt."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from v13.runtime import Runtime
from v13 import context_os as C


LONG = "An ordinary prior conversation about the garden and weather. " * 8


class Run590ContextPlanReceipts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.ctx = C.ContextOS(self.r.store, self.r.cfg)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self, query="query"):
        return self.r.store.event(self.r.session, query)["event_id"]

    def plan(self, event_id, history=None):
        return self.ctx.plan(event_id, "C3_LANGUAGE", "SYS", [], history or [], "query")

    def test_failed_cas_leaves_orphan_packet_but_cannot_train_policy(self):
        eid = self.event()
        before = self.ctx._load()[0]["policy"]
        with mock.patch.object(self.r.store, "set_state",
                               side_effect=ValueError("simulated CAS conflict")) as cas:
            with self.assertRaisesRegex(ValueError, "simulated CAS conflict"):
                self.plan(eid)
        self.assertEqual(cas.call_count, 2)
        self.assertEqual(len(self.r.store.rows(
            "SELECT * FROM packets WHERE kind='ContextPlan' AND event_id=?", (eid,))), 1)
        self.assertEqual(self.ctx._load()[0]["policy"], before)
        with self.assertRaisesRegex(ValueError, "not committed"):
            self.ctx.outcome(eid, 0.)
        self.assertEqual(self.ctx._load()[0]["policy"], before)

    def test_delayed_feedback_on_older_committed_plan_remains_valid(self):
        history = []
        for i in range(10):
            history.extend([{"event_id": f"ev{i}", "role": "user", "text": "Q" + LONG},
                            {"event_id": f"ev{i}", "role": "assistant", "text": "A" + LONG}])
        old = self.event("old")
        p = self.plan(old, history)
        self.assertTrue(any(d.startswith("compress") for d in p["plan"]["decisions"]))
        newer = self.event("newer")
        self.plan(newer)
        self.assertEqual(len(self.ctx._load()[0]["plan_receipts"]), 2)
        out = self.ctx.outcome(old, 0.)
        self.assertIn("compress", out)
        self.assertLess(out["compress"]["mean"], .5)

    def test_tampered_context_packet_is_rejected_before_policy_write(self):
        eid = self.event()
        p = self.plan(eid)
        before = self.ctx._load()[0]["policy"]
        row = self.r.store.one("SELECT id,payload FROM packets WHERE kind='ContextPlan' AND event_id=?", (eid,))
        changed = json.loads(row["payload"])
        changed["decisions"] = ["restore"]
        with self.r.store.tx() as db:
            db.execute("UPDATE packets SET payload=? WHERE id=?",
                       (json.dumps(changed), row["id"]))
        with self.assertRaisesRegex(ValueError, "digest changed"):
            self.ctx.outcome(eid, 0.)
        self.assertEqual(self.ctx._load()[0]["policy"], before)
        self.assertEqual(self.ctx._load()[0]["plan_receipts"][p["packet_id"]]["role"],
                         "C3_LANGUAGE")

    def test_bounded_receipts_evict_oldest_not_arbitrary_packet_id(self):
        with mock.patch.object(C, "MAX_PLAN_RECEIPTS", 3):
            ids = []
            for i in range(4):
                eid = self.event("turn " + str(i))
                ids.append(eid)
                self.plan(eid)
            receipts = self.ctx._load()[0]["plan_receipts"]
            self.assertEqual(len(receipts), 3)
            with self.assertRaisesRegex(ValueError, "not committed"):
                self.ctx.outcome(ids[0], .5)
            self.assertEqual(self.ctx.outcome(ids[-1], .5), {})

    def test_receipt_survives_restart_and_can_support_delayed_feedback(self):
        eid = self.event()
        p = self.plan(eid)
        receipt = self.ctx._load()[0]["plan_receipts"][p["packet_id"]]
        self.r.close()
        self.r = Runtime(self.home)
        self.ctx = C.ContextOS(self.r.store, self.r.cfg)
        self.assertEqual(self.ctx._load()[0]["plan_receipts"][p["packet_id"]], receipt)
        self.assertEqual(self.ctx.outcome(eid, .5), {})


if __name__ == "__main__":
    unittest.main()
