"""Synthetic, read/write boundary tests for independent laboratory Age 0–10."""
import json
from pathlib import Path
import tempfile
import unittest

from v13 import lab_age, effort
from v13.age import AgeControl
from v13.config import initialize
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
        current = effort.age_limits(self.age)
        self.assertEqual(current["stage"], 0)
        # Runtime compute is independent of Age; the default X10 lab exposes test rights only.
        self.assertEqual(current["focal_depth"], 3)
        self.assertEqual(current["autonomous_effort_max"], "max")
        self.assertTrue(current["tools"])
        self.assertTrue(current["deliberation"])
        self.assertTrue(current["long_loops"])
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
        self.assertEqual(limits["autonomous_effort_max"], "max")
        self.assertEqual(limits["focal_depth"], 3)
        self.assertTrue(limits["tools"])
        self.assertTrue(limits["deliberation"])
        self.assertTrue(limits["long_loops"])
        self.assertTrue(self.age.may("simple_tool_choice"))
        self.assertFalse(self.age.may("body_swap"))  # structural lock still wins
        status = lab_age.rights_status(self.age)
        self.assertEqual(status["official_stage"], 0)
        self.assertEqual(status["implemented_test_stage"], 5)
        self.assertIn("simple_tool_choice", status["newly_testable"])
        self.assertFalse(self.age.allowed("simple_tool_choice", hard_rule_block=True))
        self.assertFalse(self.age.allowed("simple_tool_choice", user_permissions={"direct_route"}))
        self.assertFalse(self.age.may("long_loops", resource_mode="RED"))
        self.age.lock_structural(False)
        self.assertTrue(self.age.may("body_swap"))
        self.assertEqual(self.age.view()["system_stage"], 0)
        hard = effort.signals("Vergleiche A und B für mein Budget", "both",
                              {"source": "BOOT_SCAFFOLD", "scaffold": "both"})
        plan = effort.decide("max", hard, age=limits, cfg={"max_reentry":2,"focal_slots":4})
        self.assertEqual(plan["age_stage"], 0)
        self.assertEqual(plan["lab_stage"], 10)
        self.assertEqual(plan["focal_cycles"], 3)
        self.assertTrue(plan["verify"])
        self.assertEqual(plan["tool_steps"], 1)

    def test_off_and_shadow_return_earned_age_limits(self):
        for mode in ("off", "shadow"):
            lab_age.save(self.home, mode=mode, stage=10)
            a = effort.age_limits(self.age)
            self.assertFalse(a["lab_compute_active"])
            self.assertEqual(a["focal_depth"], 3)
            self.assertEqual(a["autonomous_effort_max"], "max")
            self.assertFalse(a["tools"])
            self.assertFalse(a["deliberation"])
            self.assertFalse(a["long_loops"])
        lab_age.save(self.home, mode="active", stage=0)
        self.assertFalse(effort.age_limits(self.age)["lab_compute_active"])

    def test_resource_guard_does_not_change_lab_feature_selection(self):
        lab_age.save(self.home, mode="active", stage=10)
        observed = effort.age_limits(self.age, "CRITICAL")
        self.assertFalse(observed["lab_compute_active"])
        self.assertEqual(observed["lab_compute_gate"], "NOT_A_COMPUTE_SETTING")
        self.assertTrue(observed["lab_feature_test_requested"])
        self.assertEqual(observed["focal_depth"], 3)
        self.assertEqual(observed["autonomous_effort_max"], "max")
        self.assertTrue(observed["tools"])
        self.assertFalse(observed["long_loops"])  # RED resource mode still blocks long loops

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

    def test_lab_rights_are_testable_without_promoting_official_age(self):
        for level in (0, 3, 7, 10):
            with self.subTest(level=level):
                lab_age.save(self.home, mode="active", stage=level)
                green = effort.age_limits(self.age, "GREEN")
                red = effort.age_limits(self.age, "CRITICAL")
                self.assertEqual(green["stage"], 0)
                self.assertEqual(green["lab_stage"], level)
                self.assertEqual(red["lab_stage"], level)
                self.assertEqual(red["stage"], 0)
                self.assertFalse(green["lab_compute_active"])
                self.assertEqual(green["lab_feature_test_requested"], level > 0)
                self.assertFalse(red["lab_compute_active"])
                self.assertEqual(green["tools"], level >= 1)
                self.assertEqual(red["tools"], level >= 1)
                self.assertEqual(green["long_loops"], level >= 3)
                self.assertFalse(red["long_loops"])  # resource veto is independent
                self.assertFalse(self.age.may("body_swap"))  # structural lock is independent
                self.assertEqual(self.cfg["learning_mode"], "RECORD_ONLY")

    def test_config_persists_reversible_with_private_permissions(self):
        result = lab_age.save(self.home, mode="active", stage=7)
        self.assertEqual(result["mode"], "active")
        self.assertEqual(lab_age.read(self.home)["stage"], 7)
        self.assertTrue(lab_age.view(self.home)["config_persisted"])
        self.assertEqual((self.home / "config/lab-age.json").stat().st_mode & 0o077, 0)
        lab_age.save(self.home, mode="off")
        self.assertFalse(effort.age_limits(self.age)["lab_compute_active"])
        self.assertEqual(self.age.view()["system_stage"], 0)


    def test_explicit_shadow_learning_is_scoped_and_never_commits(self):
        lab_age.save(self.home, mode="active", stage=10)
        trial = lab_age.LabConfig(self.cfg, self.home)
        self.assertEqual(trial["learning_mode"], "RECORD_ONLY")
        with trial.shadow_training():
            self.assertEqual(trial["learning_mode"], "SHADOW_UPDATE")
        self.assertEqual(trial["learning_mode"], "RECORD_ONLY")

    def test_sleep_replay_batch_is_resource_limited_not_age_limited(self):
        from unittest.mock import Mock
        from v13.runtime import Runtime
        with tempfile.TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                cycle = runtime.sleep.cycle
                cycle.age.budgets = Mock(side_effect=AssertionError("Age must not supply replay budgets"))
                policy = cycle.policy()
                seen = {}
                def fake_sleep_a(st, policy_value, n, cancel, deadline, resource, **kwargs):
                    seen["n"] = n
                    return {"phase": "SLEEP_A", "status": "DONE", "selected": 0}
                cycle.sleep_a = fake_sleep_a
                report = cycle.run("wake", resource=lambda: "GREEN", origin="AUTO")
                self.assertEqual(seen["n"], policy["wake_batch"])
                self.assertEqual(report["replay_budget"], policy["wake_batch"])
                cycle.age.budgets.assert_not_called()
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
