"""Run14W integrated real SQLite witness: ContextOS, F4 World, C2/JEF and restart."""
import re
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13 import context_os as C
from v13 import neuromod as N
from v13 import effort as E

LONG = "The project garden and the weather had a long source-bound discussion. " * 8


class Run14WCrossOrgan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def context(self):
        return C.ContextOS(self.r.store, self.r.cfg, None, N.Neuromod(self.r.store))

    def event_and_context(self):
        e = self.r.store.event(self.r.session, "Run14W source-bound integrated event")
        history = []
        for i in range(12):
            history.extend([
                {"event_id": "earlier-%d" % i, "role": "user", "text": "Question %d. " % i + LONG},
                {"event_id": "earlier-%d" % i, "role": "assistant", "text": "Answer %d. " % i + LONG},
            ])
        c = self.context()
        plan = c.plan(e["event_id"], "C3_LANGUAGE", "SYS", [], history, "run14w?")
        self.assertIn("compress", " ".join(plan["plan"]["decisions"]))
        return e, c

    def action(self, e):
        forecast = self.r.world.forecast(e, "SOURCE_COPY", native_prediction=False)
        aid = self.r.store.start_action(e["event_id"], self.r.store.generation_id, forecast=forecast)
        self.r.store.finish_action(aid, "FINAL", {"role": "SOURCE_COPY", "action_duration_s": 2.0})
        return aid

    def test_one_event_context_credit_world_receipt_and_learned_wake_survive_restart(self):
        generation = self.r.store.generation_id
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")
        e, c = self.event_and_context()
        c.outcome(e["event_id"], 0.0)
        c.outcome(e["event_id"], 0.0)
        self.assertEqual(c._load()[0]["policy"]["compress"]["n"], 1)
        aid = self.action(e)
        self.assertIsNotNone(self.r.world.observe(aid))
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)
        sig = E.signals("Hallo", "simple", {"source": "BOOT_SCAFFOLD"})
        plan = E.constrain(E.plan_for(.1, sig), cfg={"max_reentry": 1, "focal_slots": 4})
        plan["learned_wake_allowed"] = True
        self.assertEqual(E.resolve_wake(plan, "both"), ("none", "LEARNED_WAKE_CAPPED"))
        self.r.close()
        self.r = Runtime(self.home)
        self.assertEqual(self.r.store.generation_id, generation)
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)
        again = self.context()
        again.outcome(e["event_id"], 0.0)
        self.assertEqual(again._load()[0]["policy"]["compress"]["n"], 1)

    def test_corrupt_world_receipt_never_credits_context_or_world_and_can_recover(self):
        e, c = self.event_and_context()
        c.outcome(e["event_id"], 0.0)
        aid = self.action(e)
        self.r.world.observe(aid)
        row = self.r.store.one("SELECT id,payload FROM packets WHERE kind='PredictionOutcome' AND event_id=?",
                               (e["event_id"],))
        altered, n = re.subn(r'("scored":(?:true|false))', r'\1,"scored":false', row["payload"], count=1)
        self.assertEqual(n, 1)
        with self.r.store.tx() as db:
            db.execute("UPDATE packets SET payload=? WHERE id=?", (altered, row["id"]))
        self.r.world._refresh(self.r.session)
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 0)
        self.assertEqual(c._load()[0]["policy"]["compress"]["n"], 1)
        self.r.world.recover()
        self.assertEqual(self.r.world.world_state()["observed_action_count"], 1)
        self.assertEqual(self.r.store.one("SELECT payload FROM packets WHERE id=?", (row["id"],))["payload"], altered)
        self.assertEqual(c._load()[0]["policy"]["compress"]["n"], 1)


if __name__ == "__main__":
    unittest.main()
