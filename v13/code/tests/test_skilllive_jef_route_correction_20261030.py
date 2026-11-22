"""SkillLive route agreement must not poison JEF's self-labelled skill outcome."""
import tempfile
import unittest
from pathlib import Path

from v13.agi import hub
from v13.agi.live import _save
from v13 import fastpolicy as fp
from v13 import jefoutcome as jo
from v13.runtime import Runtime


class SkillJEFRouteFeedback(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.lib = hub(self.r).skills
        self.lib.propose("weekly_plan", [{"route": "gist"}],
                         trigger="weekly plan", origin="USER")
        self.lib.set_stage("weekly_plan", "TRUSTED")
        self.e = self.r.store.event(self.r.session, "weekly plan")
        fp.head(self.r, "skill", self.e, "skill")
        _save(self.r.store, self.e["event_id"], skill="weekly_plan")
        self.r.store.message(self.r.session, self.e["event_id"],
                             "assistant", "Plan ready", status="FINAL")
        self.assertEqual(jo.after_turn(
            self.r, self.e, {"skill": {"name": "weekly_plan"}},
            "FINAL", {"coalition": []}), {"skill": "skill"})
        self.assertEqual(self.label()["value"], "skill")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def label(self):
        rows = (self.r.store.state(jo.KEY)[0] or {}).get("labels", [])
        return next(x for x in rows if x["event_id"] == self.e["event_id"]
                    and x["component"] == "skill")

    def test_agreeing_feedback_keeps_positive_label_and_exact_state(self):
        old_state = self.r.store.state(jo.KEY)
        self.r.memory.feedback(self.e["event_id"], "route", "gist")
        self.assertEqual(self.lib.get("weekly_plan")["stage"], "TRUSTED")
        self.assertEqual(self.label()["value"], "skill")
        self.assertEqual(self.r.store.state(jo.KEY), old_state)
        self.assertEqual(jo.report(self.r)["heads"]["skill"]["by_value"],
                         {"skill": 1})
        self.assertEqual(self.r.pool.pids(), [])

    def test_disagreeing_feedback_reopens_and_invalidates_exactly_once(self):
        old_source = self.label()["source_id"]
        self.r.memory.feedback(self.e["event_id"], "route", "detail")
        self.assertEqual(self.lib.get("weekly_plan")["stage"], "SHADOW")
        self.assertEqual(self.label()["value"], "none")
        self.assertNotEqual(self.label()["source_id"], old_source)
        self.assertEqual(jo.report(self.r)["heads"]["skill"]["by_value"],
                         {"none": 1})
        state = self.r.store.state(jo.KEY)
        self.r.memory.feedback(self.e["event_id"], "route", "detail")
        self.assertEqual(self.r.store.state(jo.KEY)[0]["labels"],
                         state[0]["labels"])
        self.assertEqual(self.r.pool.pids(), [])

    def test_agreement_remains_correct_after_sqlite_restart(self):
        session = self.r.session
        eid = self.e["event_id"]
        before = self.r.store.state(jo.KEY)
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.lib = hub(self.r).skills
        self.assertEqual(self.r.session, session)
        self.r.memory.feedback(eid, "route", "gist")
        self.assertEqual(self.r.store.state(jo.KEY), before)
        self.assertEqual(self.lib.get("weekly_plan")["stage"], "TRUSTED")
        self.assertEqual(self.label()["value"], "skill")


if __name__ == "__main__":
    unittest.main()
