"""Run586: a GOAL_WAKE event cannot borrow USER authority for a SELF/SYSTEM goal."""
from pathlib import Path
import tempfile
import unittest

from v13.config import initialize
from v13.store import Store
from v13.scheduler import EventScheduler
from v13.age import AgeControl
from v13.agi.goals import GoalStore


class AllowedAge:
    """Synthetic permission stub, not a production Age promotion."""
    def may(self, right, resource_mode="GREEN"):
        return right in {"choose_learning_goals", "resume_open_goals"}


class Run586GoalOriginAge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.store = Store(self.home)
        self.goals = GoalStore(self.store, age=AgeControl(self.store, self.cfg))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    @staticmethod
    def event(gid, origin="USER", kind="GOAL_WAKE", action="growth_goal"):
        return {"kind": kind, "action": action, "origin": origin,
                "payload": {"goal_id": gid}}

    def test_forged_user_event_cannot_wake_system_goal(self):
        gid = self.goals.add("System review", origin="SYSTEM", steps=["review"])
        self.assertEqual(self.goals.on_wake(self.event(gid))["status"],
                         "GOAL_ORIGIN_MISMATCH")
        self.assertEqual(self.goals.on_wake(self.event(gid, "SELF"))["status"],
                         "HELD_AGE")
        self.assertEqual(self.goals.get(gid)["status"], "OPEN")

    def test_forged_user_event_cannot_wake_self_goal(self):
        allowed = GoalStore(self.store, age=AllowedAge())
        gid = allowed.add("Own idea", origin="SELF", steps=["think"])
        self.assertEqual(self.goals.on_wake(self.event(gid))["status"],
                         "GOAL_ORIGIN_MISMATCH")
        self.assertEqual(self.goals.on_wake(self.event(gid, "SELF"))["status"],
                         "HELD_AGE")
        self.assertEqual(self.goals.get(gid)["status"], "OPEN")

    def test_real_scheduler_dispatch_user_origin_does_not_override_goal_origin(self):
        gid = self.goals.add("System goal", origin="SYSTEM")
        scheduler = EventScheduler(self.store, self.cfg, clock=lambda: 1700000000.,
                                   age=AgeControl(self.store, self.cfg),
                                   key="G13_RUN586_ORIGIN_TEST")
        eid = scheduler.post("GOAL_WAKE", origin="USER", action="growth_goal",
                             payload={"goal_id": gid})
        dispatched = scheduler.next()
        self.assertEqual(dispatched["id"], eid)
        self.assertEqual(dispatched["origin"], "USER")
        self.assertEqual(self.goals.on_wake(dispatched)["status"],
                         "GOAL_ORIGIN_MISMATCH")
        self.assertEqual(self.goals.get(gid)["status"], "OPEN")
        scheduler.complete(eid, "DONE")

    def test_correct_self_event_requires_age_right_even_if_not_from_scheduler(self):
        gid = self.goals.add("System goal", origin="SYSTEM")
        self.assertEqual(self.goals.on_wake(self.event(gid, "SELF"))["status"],
                         "HELD_AGE")
        self.assertEqual(self.goals.get(gid)["status"], "OPEN")
        # Synthetic granted controller proves the structural positive path only.
        permitted = GoalStore(self.store, age=AllowedAge())
        self.assertEqual(permitted.on_wake(self.event(gid, "SELF"))["status"], "WOKEN")
        self.assertEqual(permitted.get(gid)["status"], "ACTIVE")

    def test_user_goal_requires_user_event_and_keeps_subtree_scope(self):
        gid = self.goals.add("Aurora", steps=["plan"])
        foreign = self.goals.add("Borealis", steps=["plan"])
        self.goals.add("Borealis child", parent=foreign, steps=["child"])
        for origin in ("SELF", "SYSTEM", None):
            with self.subTest(origin=origin):
                self.assertEqual(self.goals.on_wake(self.event(gid, origin))["status"],
                                 "GOAL_ORIGIN_MISMATCH")
                self.assertEqual(self.goals.get(gid)["status"], "OPEN")
        out = self.goals.on_wake(self.event(gid, "USER"))
        self.assertEqual(out["next"], {"goal_id": gid, "step": 0})
        self.assertEqual(self.goals.get(foreign)["status"], "OPEN")

    def test_missing_or_wrong_kind_action_never_activates_goal(self):
        gid = self.goals.add("Aurora", steps=["plan"])
        for kind, action in (("TIMER", "growth_goal"),
                             ("GOAL_WAKE", "growth_eval"),
                             (None, "growth_goal"),
                             ("GOAL_WAKE", None)):
            with self.subTest(kind=kind, action=action):
                self.assertEqual(self.goals.on_wake(self.event(gid, kind=kind,
                                                                action=action))["status"],
                                 "INVALID_WAKE_EVENT")
                self.assertEqual(self.goals.get(gid)["status"], "OPEN")


if __name__ == "__main__":
    unittest.main()
