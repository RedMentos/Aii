"""Run588: real Termux operator exposes atomic USER subgoal plans, never model authority."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from v13.runtime import Runtime
from v13.operator import Operator
from v13.agi import hub


class Run588GoalPlanOperator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.op = Operator(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def root(self, title="Plan Aurora"):
        out = self.op.run(":growth goal " + title)
        self.assertTrue(out.startswith("Ziel angelegt: goal_"))
        return out.split()[-1]

    def children(self, parent):
        return [g for g in hub(self.r).goals.tree() if g["parent"] == parent]

    def test_real_tty_multititle_plan_and_restart(self):
        gid = self.root()
        out = json.loads(self.op.run(":growth goal subgoals " + gid +
                                     " Daten sammeln | Modelle prüfen | Bericht schreiben"))
        self.assertEqual(out["parent"], gid)
        self.assertEqual(out["count"], 3)
        self.assertEqual(out["authority"], "EXPLICIT_USER_OPERATOR")
        self.assertEqual([g["title"] for g in self.children(gid)],
                         ["Daten sammeln", "Modelle prüfen", "Bericht schreiben"])
        self.assertEqual([g["id"] for g in self.children(gid)], out["children"])
        self.r.close()
        self.r = Runtime(self.home)
        self.op = Operator(self.r)
        self.assertEqual([g["id"] for g in self.children(gid)], out["children"])
        self.assertEqual(hub(self.r).goals.get(gid)["origin"], "USER")

    def test_malformed_separators_blank_titles_and_missing_args_do_not_write(self):
        gid = self.root()
        before = hub(self.r).goals.box.load()
        for suffix in ("", " | Second", "First |", "First | | Second", '""'):
            with self.subTest(suffix=suffix):
                with self.assertRaises(ValueError):
                    self.op.run(":growth goal subgoals " + gid + " " + suffix)
                self.assertEqual(hub(self.r).goals.box.load(), before)

    def test_over_32_children_is_rejected_atomically(self):
        gid = self.root()
        before = hub(self.r).goals.box.load()
        cmd = ":growth goal subgoals " + gid + " " + " | ".join("step" + str(i) for i in range(33))
        with self.assertRaises(ValueError):
            self.op.run(cmd)
        self.assertEqual(hub(self.r).goals.box.load(), before)

    def test_unknown_and_non_user_parent_cannot_receive_operator_children(self):
        gid = self.root()
        with self.assertRaises(KeyError):
            self.op.run(":growth goal subgoals goal_missing Child")
        system = hub(self.r).goals.add("System", origin="SYSTEM")
        with mock.patch("v13.agi.goals.age_allows", return_value=True):
            own = hub(self.r).goals.add("Self", origin="SELF")
        for parent in (system, own):
            with self.subTest(parent=parent):
                with self.assertRaises(PermissionError):
                    self.op.run(":growth goal subgoals " + parent + " Child")
                self.assertEqual(self.children(parent), [])
        self.assertEqual(self.children(gid), [])

    def test_closed_parent_requires_explicit_reopen(self):
        gid = self.root()
        self.assertEqual(json.loads(self.op.run(":growth goal done " + gid))["status"], "DONE")
        with self.assertRaisesRegex(ValueError, "GOAL_CLOSED_REOPEN_FIRST"):
            self.op.run(":growth goal subgoals " + gid + " Child")
        self.assertEqual(self.children(gid), [])
        self.op.run(":growth goal reopen " + gid)
        out = json.loads(self.op.run(":growth goal subgoals " + gid + " Child"))
        self.assertEqual(out["count"], 1)

    def test_model_origin_command_refused_without_plan_change(self):
        gid = self.root()
        cmd = ":growth goal subgoals " + gid + " Child"
        with self.assertRaises(ValueError):
            self.op.run(cmd, origin="MODEL")
        self.assertEqual(self.children(gid), [])

    def test_help_and_german_guide_expose_real_command(self):
        self.assertIn("subgoals", self.op.run(":help"))
        guide = self.op.run(":befehle Unterziele")
        self.assertIn(":growth goal subgoals", guide)
        self.assertIn("zusammen gespeichert", guide)
        gid = self.root("Andere Aufgabe")
        self.assertEqual(json.loads(self.op.run(":growth goal status " + gid))["status"], "OPEN")


if __name__ == "__main__":
    unittest.main()
