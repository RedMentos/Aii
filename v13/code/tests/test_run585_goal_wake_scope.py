"""Run585 AG3 GOAL_WAKE subtree isolation; SQLite software proof, no models."""
from pathlib import Path
import tempfile
import unittest

from v13.store import Store
from v13.config import initialize
from v13.agi.goals import GoalStore


class Run585GoalWakeScope(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        initialize(self.home)
        self.store = Store(self.home)
        self.goals = GoalStore(self.store, clock=lambda: 1700000000.)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def wake(self, gid):
        return self.goals.on_wake({"kind": "GOAL_WAKE", "origin": "USER",
                                   "action": "growth_goal", "payload": {"goal_id": gid}})

    def test_unrelated_deeper_goal_cannot_hijack_requested_wake(self):
        a = self.goals.add("Project Aurora", steps=["plan Aurora"])
        b = self.goals.add("Project Borealis", steps=["plan Borealis"])
        bc = self.goals.add("Borealis child", parent=b, steps=["foreign child"])
        self.assertEqual(self.goals.next_actionable()["goal"]["id"], bc)
        result = self.wake(a)
        self.assertEqual(result["status"], "WOKEN")
        self.assertEqual(result["next"], {"goal_id": a, "step": 0})
        self.assertEqual(self.goals.get(a)["status"], "ACTIVE")
        self.assertEqual(self.goals.get(bc)["status"], "OPEN")

    def test_parent_wake_chooses_only_its_deepest_open_child(self):
        a = self.goals.add("Aurora parent", steps=["parent step"])
        child = self.goals.add("Aurora child", parent=a, steps=["child step"])
        foreign = self.goals.add("Foreign project", steps=["foreign"])
        self.goals.add("Foreign child", parent=foreign, steps=["foreign"])
        self.goals.add("Foreign grandchild", parent=self.goals.tree()[-1]["id"],
                       steps=["foreign"])
        self.assertEqual(self.wake(a)["next"], {"goal_id": child, "step": 0})

    def test_blocked_root_does_not_wake_other_goal(self):
        a = self.goals.add("Blocked Aurora", steps=["a"])
        b = self.goals.add("Unrelated Borealis", steps=["b"])
        self.goals.set_status(a, "BLOCKED")
        result = self.wake(a)
        self.assertEqual(result, {"status": "GOAL_BLOCKED", "goal_id": a, "next": None})
        self.assertEqual(self.goals.get(a)["status"], "BLOCKED")
        self.assertEqual(self.goals.get(b)["status"], "OPEN")

    def test_closed_unknown_and_malformed_payload_fail_closed(self):
        a = self.goals.add("Finished Aurora", steps=["a"])
        self.goals.set_status(a, "DONE")
        self.assertEqual(self.wake(a), {"status": "GOAL_CLOSED", "goal_id": a})
        self.assertEqual(self.wake("goal_missing"), {"status": "UNKNOWN_GOAL"})
        for payload in (None, "", [], {"goal_id": []}, {"goal_id": ""}):
            with self.subTest(payload=payload):
                self.assertEqual(self.goals.on_wake({"payload": payload}),
                                 {"status": "UNKNOWN_GOAL"})
        self.assertEqual(self.goals.get(a)["status"], "DONE")

    def test_closed_ancestor_excludes_open_descendant(self):
        root = self.goals.add("Aurora", steps=["root"])
        child = self.goals.add("Child", parent=root, steps=["child"])
        self.goals.set_status(child, "DONE")
        # A later open grandchild of a closed child cannot be selected by a root wake.
        grandchild = self.goals.add("Grandchild", parent=child, steps=["grandchild"])
        self.assertEqual(self.wake(root)["next"], {"goal_id": root, "step": 0})
        self.assertEqual(self.goals.get(grandchild)["status"], "OPEN")

    def test_sqlite_restart_preserves_goal_tree_scope(self):
        a = self.goals.add("Aurora", steps=["a"])
        b = self.goals.add("Borealis", steps=["b"])
        self.goals.add("Borealis child", parent=b, steps=["b child"])
        self.store.close()
        self.store = Store(self.home)
        self.goals = GoalStore(self.store, clock=lambda: 1700000000.)
        self.assertEqual(self.wake(a)["next"], {"goal_id": a, "step": 0})
        self.assertEqual(self.goals.get(a)["status"], "ACTIVE")
        self.assertEqual(self.goals.report()["next"]["goal"]["title"], "Borealis child")


if __name__ == "__main__":
    unittest.main()
