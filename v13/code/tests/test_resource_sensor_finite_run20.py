"""Run20 test-first: malformed live resource readings must not silently return GREEN."""
import math
import unittest

from v13 import resource_modes as rm
from v13.resources import ResourceGuard

CFG = {"minimum_free_mb": 500, "thermal_limit_c": 45.0}
MB = 1048576


def snapshot(mem=4000*MB, temp=30.0, processes=None):
    return {"mem_available_bytes": mem, "battery_temperature_c": temp,
            "processes": [] if processes is None else processes}


class ResourceSensorFinite(unittest.TestCase):
    def setUp(self):
        self.boot = rm.boot_profile(CFG, {"android": False})

    def test_finite_modes_and_unmeasured_none_remain_unchanged(self):
        for mem, temp, expected in (
            (4000*MB, 30.0, "GREEN"),
            (1400*MB, 30.0, "YELLOW"),
            (900*MB, 30.0, "ORANGE"),
            (400*MB, 30.0, "RED"),
            (None, None, "GREEN"),
        ):
            with self.subTest(mem=mem, temp=temp):
                self.assertEqual(rm.classify(snapshot(mem, temp), self.boot)[0], expected)

    def test_invalid_memory_and_thermal_never_look_green(self):
        invalid = (
            ("mem", float("nan")), ("mem", float("inf")),
            ("mem", float("-inf")), ("mem", True),
            ("mem", -1), ("mem", "unknown"),
            ("temp", float("nan")), ("temp", float("inf")),
            ("temp", float("-inf")), ("temp", True),
            ("temp", "unknown"),
        )
        for key, value in invalid:
            with self.subTest(key=key, value=repr(value)):
                snap = snapshot()
                snap["mem_available_bytes" if key == "mem" else "battery_temperature_c"] = value
                mode, reasons = rm.classify(snap, self.boot, previous="GREEN")
                self.assertEqual(mode, "YELLOW")
                self.assertTrue(any("INVALID" in reason for reason in reasons))

    def test_invalid_sensor_never_downgrades_prior_orange_or_red(self):
        snap = snapshot(mem=float("nan"))
        self.assertEqual(rm.classify(snap, self.boot, previous="ORANGE")[0], "ORANGE")
        self.assertEqual(rm.classify(snap, self.boot, previous="RED")[0], "RED")
        guard = ResourceGuard(CFG, profile=self.boot)
        self.assertEqual(guard.update(snapshot(mem=900*MB)), "PRESSURE")
        self.assertEqual(guard.mode, "ORANGE")
        self.assertEqual(guard.update(snap), "PRESSURE")
        self.assertEqual(guard.mode, "ORANGE")
        self.assertTrue(any("INVALID" in reason for reason in guard.reasons))

    def test_invalid_process_rss_pss_fail_closed_only_when_profile_uses_rss(self):
        profile = rm.boot_profile(CFG, {"android": True})
        for field, value in (
            ("rss_bytes", float("nan")),
            ("rss_bytes", float("inf")),
            ("rss_bytes", -1),
            ("rss_bytes", True),
            ("pss_bytes", float("nan")),
            ("pss_bytes", float("inf")),
            ("pss_bytes", -1),
            ("pss_bytes", True),
        ):
            with self.subTest(field=field, value=repr(value)):
                proc = {"rss_bytes": 200*MB, "pss_bytes": None}
                proc[field] = value
                mode, reasons = rm.classify(snapshot(processes=[proc]), profile)
                self.assertEqual(mode, "YELLOW")
                self.assertTrue(any("INVALID" in reason for reason in reasons))
        self.assertEqual(rm.classify(snapshot(processes=[{"rss_bytes": None, "pss_bytes": None}]), profile)[0],
                         "GREEN")


if __name__ == "__main__":
    unittest.main()
