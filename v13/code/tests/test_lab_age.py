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

    def test_initially_level_ten_shadow_and_official_age_zero(self):
        v = lab_age.view(self.home, official_stage=self.age.system_stage())
        self.assertEqual(v["stage"], 10)
        self.assertEqual(v["mode"], "shadow")
        self.assertTrue(v["test_only"])
        self.assertEqual(self.age.view()["system_stage"], 0)
        current = effort.age_limits(self.age)
        self.assertEqual(current["stage"], 0)
        self.assertEqual(current["focal_depth"], 1)
        self.assertEqual(current["autonomous_effort_max"], "low")

    def test_active_level_ten_increases_compute_not_tool_rights(self):
        lab_age.save(self.home, mode="active", stage=10)
        limits = effort.age_limits(self.age)
        self.assertEqual(limits["stage"], 0)
        self.assertEqual(limits["lab_stage"], 10)
        self.assertTrue(limits["lab_compute_active"])
        self.assertEqual(limits["autonomous_effort_max"], "max")
        self.assertEqual(limits["focal_depth"], 3)
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
            self.assertEqual(a["focal_depth"], 1)
            self.assertEqual(a["autonomous_effort_max"], "low")
        lab_age.save(self.home, mode="active", stage=0)
        self.assertFalse(effort.age_limits(self.age)["lab_compute_active"])

    def test_resource_guard_still_blocks_extra_compute(self):
        lab_age.save(self.home, mode="active", stage=10)
        observed = effort.age_limits(self.age, "CRITICAL")
        self.assertFalse(observed["lab_compute_active"] is False and observed["focal_depth"] != 1)
        self.assertEqual(observed["focal_depth"], 1)
        self.assertEqual(observed["autonomous_effort_max"], "low")

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

    def test_config_persists_reversible_with_private_permissions(self):
        result = lab_age.save(self.home, mode="active", stage=7)
        self.assertEqual(result["mode"], "active")
        self.assertEqual(lab_age.read(self.home)["stage"], 7)
        self.assertEqual((self.home / "config/lab-age.json").stat().st_mode & 0o077, 0)
        lab_age.save(self.home, mode="off")
        self.assertFalse(effort.age_limits(self.age)["lab_compute_active"])
        self.assertEqual(self.age.view()["system_stage"], 0)


if __name__ == "__main__":
    unittest.main()
