"""Run587: AG3 plan decomposition is one durable CAS, never a partial list."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from v13.config import initialize
from v13.store import Store
from v13.agi.goals import GoalStore


class BadTitle:
    def __str__(self):
        raise RuntimeError("title conversion failed")


class Run587AtomicDecomposition(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        initialize(self.home)
        self.store = Store(self.home)
        self.goals = GoalStore(self.store, clock=lambda: 1700000000.)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def snapshot(self):
        return self.goals.box.load()[0]

    def test_two_children_commit_together_and_survive_restart(self):
        parent = self.goals.add("Aurora", steps=["parent step"])
        ids = self.goals.decompose(parent, ["numbers", "colours"])
        self.assertEqual(len(ids), 2)
        self.assertEqual([self.goals.get(i)["parent"] for i in ids], [parent, parent])
        self.assertEqual([self.goals.get(i)["title"] for i in ids],
                         ["numbers", "colours"])
        self.assertEqual([int(i.split("_")[1]) for i in ids],
                         [int(parent.split("_")[1]) + 1, int(parent.split("_")[1]) + 2])
        self.store.close()
        self.store = Store(self.home)
        self.goals = GoalStore(self.store, clock=lambda: 1700000000.)
        self.assertEqual([self.goals.get(i)["title"] for i in ids],
                         ["numbers", "colours"])
        self.assertEqual(self.goals.next_actionable(root_id=parent)["goal"]["id"],
                         ids[0])

    def test_capacity_failure_does_not_commit_first_child(self):
        with mock.patch("v13.agi.goals.MAX_GOALS", 4):
            parent = self.goals.add("parent")
            self.goals.add("other")
            self.goals.add("another")
            before = self.snapshot()
            with self.assertRaisesRegex(ValueError, "Ziel-Speicher voll"):
                self.goals.decompose(parent, ["one", "two"])
            self.assertEqual(self.snapshot(), before)

    def test_late_bad_title_conversion_leaves_no_children(self):
        parent = self.goals.add("parent")
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, "title conversion failed"):
            self.goals.decompose(parent, (x for x in ["first", "second", BadTitle()]))
        self.assertEqual(self.snapshot(), before)

    def test_oversized_generator_fails_without_partial_commit(self):
        parent = self.goals.add("parent")
        before = self.snapshot()
        with mock.patch("v13.agi.goals.MAX_GOALS", 4):
            with self.assertRaisesRegex(ValueError, "Ziel-Speicher voll"):
                self.goals.decompose(parent, (f"child-{i}" for i in range(20)))
        self.assertEqual(self.snapshot(), before)

    def test_empty_plan_is_no_op_without_version_change(self):
        parent = self.goals.add("parent")
        before, version = self.goals.box.load()
        self.assertEqual(self.goals.decompose(parent, []), [])
        after, later = self.goals.box.load()
        self.assertEqual((after, later), (before, version))

    def test_invalid_parent_depth_and_age_fail_without_writes(self):
        with self.assertRaises(KeyError):
            self.goals.decompose("goal_missing", ["x"])
        parent = self.goals.add("root")
        cur = parent
        for depth in range(5):
            cur = self.goals.add("level", parent=cur)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "Zieltiefe"):
            self.goals.decompose(cur, ["too deep"])
        self.assertEqual(self.snapshot(), before)
        with self.assertRaises(PermissionError):
            self.goals.decompose(parent, ["self"], origin="SELF")
        self.assertEqual(self.snapshot(), before)

    def test_one_optimistic_cas_conflict_retries_exactly_once(self):
        parent = self.goals.add("parent")
        original = self.store.set_state
        seen = {"failed": False}
        def fail_once(key, *args, **kwargs):
            if key == "G3_GOALS" and not seen["failed"]:
                seen["failed"] = True
                raise ValueError("simulated CAS conflict")
            return original(key, *args, **kwargs)
        with mock.patch.object(self.store, "set_state", side_effect=fail_once):
            ids = self.goals.decompose(parent, ["one", "two"])
        self.assertTrue(seen["failed"])
        self.assertEqual(len(ids), 2)
        self.assertEqual([g["id"] for g in self.goals.tree() if g["parent"] == parent],
                         ids)
        self.assertEqual(self.snapshot()["seq"], 3)


if __name__ == "__main__":
    unittest.main()
