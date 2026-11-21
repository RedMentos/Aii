"""Synthetic, read/write boundary tests for independent laboratory Age 0–10."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from v13 import lab_age, effort
from v13.age import AgeControl
from v13.config import initialize

# Keep goal-wake lifecycle regressions in this existing QA workflow's trigger set.
from test_goal_wake_atomicity_20261121 import GoalWakeAtomicityTests
from v13.store import Store


class LabAgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.cfg = initialize(self.home)
        self.store = Store(self.home)
        self.addCleanup(self.store.close)
        self.age = AgeControl(self.store, self.cfg)

    def test_initially_owner_requested_level_ten_active_and_official_age_zero(self):
        v = lab_age.view(self.home, official_stage=self.age.system_stage())
        self.assertEqual(v["stage"], 10)
        self.assertEqual(v["mode"], "active")
        self.assertTrue(v["feature_test_requested"])
        self.assertFalse(v["compute_requested"])
        self.assertFalse(v["config_persisted"])
        self.assertTrue(v["test_only"])
        self.assertEqual(self.age.view()["system_stage"], 0)
        with mock.patch.object(self.age, 'budgets', side_effect=AssertionError('Age budget read')):
            current = effort.age_limits(self.age)
        self.assertEqual(current["stage"], 0)
        # The laboratory selector never scales CPU/effort budgets.
        self.assertNotIn("focal_depth", current)
        self.assertNotIn("autonomous_effort_max", current)
        self.assertTrue(current["lab_feature_test_requested"])
        self.assertFalse(current["lab_compute_active"])
        self.assertEqual(current["lab_compute_gate"], "NOT_A_COMPUTE_SETTING")

    def test_active_level_ten_does_not_change_compute_or_earned_permissions(self):
        lab_age.save(self.home, mode="active", stage=10)
        limits = effort.age_limits(self.age)
        self.assertEqual(limits["stage"], 0)
        self.assertEqual(limits["lab_stage"], 10)
        self.assertTrue(limits["lab_feature_test_requested"])
        self.assertFalse(limits["lab_compute_active"])
        self.assertNotIn("autonomous_effort_max", limits)
        self.assertNotIn("focal_depth", limits)
        self.assertFalse(limits["tools"])
        self.assertFalse(limits["deliberation"])
        self.assertFalse(self.age.may("simple_tool_choice"))
        self.assertFalse(self.age.may("body_swap"))
        self.assertEqual(self.age.view()["system_stage"], 0)
        hard = effort.signals("Vergleiche A und B für mein Budget", "both",
                              {"source": "BOOT_SCAFFOLD", "scaffold": "both"})
        plan = effort.decide("max", hard, age=limits, cfg={"max_reentry":2,"focal_slots":4})
        self.assertEqual(plan["age_stage"], 0)
        self.assertEqual(plan["lab_stage"], 10)
        self.assertEqual(plan["focal_cycles"], 3)
        self.assertFalse(plan["verify"])
        self.assertEqual(plan["tool_steps"], 0)

    def test_off_and_shadow_return_earned_age_limits(self):
        for mode in ("off", "shadow"):
            lab_age.save(self.home, mode=mode, stage=10)
            a = effort.age_limits(self.age)
            self.assertFalse(a["lab_compute_active"])
            self.assertNotIn("focal_depth", a)
            self.assertNotIn("autonomous_effort_max", a)
        lab_age.save(self.home, mode="active", stage=0)
        self.assertFalse(effort.age_limits(self.age)["lab_compute_active"])

    def test_resource_guard_does_not_change_lab_feature_selection(self):
        lab_age.save(self.home, mode="active", stage=10)
        observed = effort.age_limits(self.age, "CRITICAL")
        self.assertFalse(observed["lab_compute_active"])
        self.assertEqual(observed["lab_compute_gate"], "NOT_A_COMPUTE_SETTING")
        self.assertTrue(observed["lab_feature_test_requested"])
        self.assertEqual(observed["resource_mode"], "RED")
        self.assertNotIn("focal_depth", observed)
        self.assertNotIn("autonomous_effort_max", observed)

    def test_invalid_or_symlink_configuration_fails_closed(self):
        path = self.home / "config/lab-age.json"
        path.write_text('{"schema":"v13.lab-age/1","stage":10,"mode":"invalid"}')
        self.assertEqual(lab_age.read(self.home)["mode"], "off")
        path.unlink()
        external = self.home / "external.json"
        external.write_text("private")
        path.symlink_to(external)
        self.assertEqual(lab_age.read(self.home)["mode"], "off")
        with self.assertRaises(ValueError):
            lab_age.save(self.home, mode="active", stage=10)
        self.assertEqual(external.read_text(), "private")

    def test_out_of_bounds_and_bad_types_rejected(self):
        for x in (11, -1, 4.5, True, "10"):
            with self.assertRaises(ValueError):
                lab_age.save(self.home, stage=x)
        with self.assertRaises(ValueError):
            lab_age.save(self.home, mode="unlock_permissions")
        self.assertFalse((self.home / "config/lab-age.json").exists())

    def test_neither_requested_lab_stage_nor_thermal_block_changes_earned_age(self):
        signatures=[]
        hot=effort.signals("Vergleiche A und B","both",{"source":"BOOT_SCAFFOLD","scaffold":"both"}) | {
            "uncertainty":1.,"conflict":1.,"novelty":1.,"salience":1.}
        for level in (0, 3, 7, 10):
            with self.subTest(level=level):
                lab_age.save(self.home, mode="active", stage=level)
                green = effort.age_limits(self.age, "NORMAL")
                red = effort.age_limits(self.age, "CRITICAL")
                self.assertEqual(green["stage"], 0)
                self.assertEqual(green["lab_stage"], level)
                self.assertEqual(red["lab_stage"], level)
                self.assertEqual(red["stage"], 0)
                self.assertFalse(green["lab_compute_active"])
                self.assertEqual(green["lab_feature_test_requested"], level > 0)
                self.assertFalse(red["lab_compute_active"])
                self.assertEqual(red["resource_mode"], "RED")
                self.assertFalse(self.age.may("simple_tool_choice"))
                self.assertFalse(self.age.may("body_swap"))
                self.assertEqual(self.cfg["learning_mode"], "RECORD_ONLY")
                signatures.append(tuple(effort.decide("adaptive",hot,age=green)[k] for k in
                    ("effort","band","wake","max_reentry","focal_cycles","focal_slots","observer_scale")))
        self.assertTrue(all(x==signatures[0] for x in signatures[1:]))

    def test_sleep_replay_quantity_uses_policy_and_resource_not_age_budgets(self):
        from v13.sleep import SleepCycle
        class NoBudgetAge:
            def may(self,*args,**kwargs):return False
            def budgets(self,*args,**kwargs):raise AssertionError("Age cannot cap replay quantity")
        cycle=SleepCycle(self.store,self.cfg,None,age=NoBudgetAge(),home=self.home)
        report=cycle.run(mode="wake",resource=lambda:"NORMAL",origin="SYSTEM",batch=2)
        self.assertEqual(report["replay_budget"],2)
        self.assertEqual(report["status"],"DONE")

    def test_learning_limits_do_not_call_age_budget_api(self):
        from v13.agi.base import learning_limit
        with mock.patch.object(self.age,"budgets",side_effect=AssertionError("Age budget read")):
            self.assertEqual(learning_limit(self.age,"goal_depth",1),1)
            self.assertEqual(learning_limit(self.age,"exploration_rate",0.,capability="tool"),0.)

    def test_age_compute_consumers_do_not_call_budget_api(self):
        import ast
        root=Path(__file__).resolve().parents[1]/"v13"
        allowed={"age.py","lab_age_runtime.py"}
        for source in root.rglob("*.py"):
            if source.name in allowed:continue
            tree=ast.parse(source.read_text(encoding="utf-8"))
            calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and
                   isinstance(n.func,ast.Attribute) and n.func.attr=="budgets"]
            self.assertEqual(calls,[],str(source.relative_to(root)))

    def test_config_persists_reversible_with_private_permissions(self):
        result = lab_age.save(self.home, mode="active", stage=7)
        self.assertEqual(result["mode"], "active")
        self.assertEqual(lab_age.read(self.home)["stage"], 7)
        self.assertTrue(lab_age.view(self.home)["config_persisted"])
        self.assertEqual((self.home / "config/lab-age.json").stat().st_mode & 0o077, 0)
        lab_age.save(self.home, mode="off")
        self.assertFalse(effort.age_limits(self.age)["lab_compute_active"])
        self.assertEqual(self.age.view()["system_stage"], 0)


if __name__ == "__main__":
    unittest.main()
