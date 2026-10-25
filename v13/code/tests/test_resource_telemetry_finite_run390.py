"""Run390 preregistered source-only resource telemetry fail-closed counterexamples.

A missing reading (None) remains the existing unmeasured state; a *present*
malformed reading must never be interpreted as a measured safe GREEN state.
"""
import copy
import math
import unittest

from v13 import resource_modes as rm
from v13.resources import ResourceGuard


MB = 1048576
CFG = {"minimum_free_mb": 500, "thermal_limit_c": 45.0}


def snap(mem=4000, temp=30, processes=None):
    return {
        "mem_available_bytes": int(mem * MB) if isinstance(mem, int) and not isinstance(mem, bool) else mem,
        "battery_temperature_c": temp,
        "processes": [] if processes is None else processes,
    }


class FiniteResourceTelemetry(unittest.TestCase):
    def setUp(self):
        self.profile = rm.boot_profile(CFG, {"android": False})

    def assert_invalid(self, reading, reason):
        mode, reasons = rm.classify(reading, self.profile)
        self.assertEqual(mode, "RED", (reading, reasons))
        self.assertIn(reason, reasons)

    def test_invalid_available_memory_is_never_green_or_exception(self):
        for value in (float("nan"), float("inf"), -float("inf"), True, False, -1, "4000", "invalid"):
            with self.subTest(value=repr(value)):
                self.assert_invalid(snap(value), "INVALID_MEM_AVAILABLE")

    def test_invalid_temperature_is_never_green_or_exception(self):
        for value in (float("nan"), float("inf"), -float("inf"), True, False, "30", "invalid"):
            with self.subTest(value=repr(value)):
                self.assert_invalid(snap(temp=value), "INVALID_BATTERY_TEMPERATURE")

    def test_configured_rss_rejects_invalid_process_metrics(self):
        self.profile = rm.boot_profile(CFG, {"android": True})
        for record in (
            {"rss_bytes": float("nan")}, {"pss_bytes": float("inf")},
            {"rss_bytes": True}, {"pss_bytes": False},
            {"rss_bytes": -1}, {"pss_bytes": "9000"},
        ):
            with self.subTest(record=repr(record)):
                self.assert_invalid(snap(processes=[record]), "INVALID_PROCESS_MEMORY")
        for bad in ("not-a-list", {"rss_bytes": 100}, [42], [None]):
            with self.subTest(container=repr(bad)):
                self.assert_invalid(snap(processes=bad), "INVALID_PROCESS_MEMORY")

    def test_missing_process_metrics_do_not_fabricate_measured_rss(self):
        self.profile = rm.boot_profile(CFG, {"android": True})
        self.assertIsNone(rm.total_rss_mb({"processes": [{"rss_bytes": None, "pss_bytes": None}]}))
        self.assertEqual(rm.classify(snap(processes=[{"rss_bytes": None, "pss_bytes": None}]), self.profile)[0], "GREEN")

    def test_nonfinite_profile_thresholds_and_hysteresis_are_rejected(self):
        cases = (
            ("mem_mb", "YELLOW", float("nan")),
            ("mem_mb", "ORANGE", float("inf")),
            ("mem_mb", "RED", True),
            ("mem_mb", "RED", -1),
            ("temp_c", "YELLOW", float("-inf")),
            ("temp_c", "ORANGE", False),
            ("hysteresis", "mem_fraction", float("nan")),
            ("hysteresis", "mem_fraction", -0.1),
            ("hysteresis", "temp_c", float("inf")),
            ("hysteresis", "temp_c", True),
        )
        for section, key, value in cases:
            with self.subTest(section=section, key=key, value=repr(value)):
                p = copy.deepcopy(self.profile)
                p[section][key] = value
                with self.assertRaises((ValueError, TypeError, KeyError)):
                    rm.validate(p)
        p = rm.boot_profile(CFG, {"android": True})
        p["rss_mb"]["YELLOW"] = float("nan")
        with self.assertRaises((ValueError, TypeError, KeyError)):
            rm.validate(p)

    def test_corrupt_persisted_profile_falls_back_to_uncalibrated_boot(self):
        p = copy.deepcopy(self.profile)
        p["mem_mb"]["YELLOW"] = float("nan")

        class FakeStore:
            def state(self, key, default):
                return p, 1

        loaded = rm.load_profile(FakeStore(), CFG)
        self.assertEqual(loaded["status"], "UNCALIBRATED")
        self.assertEqual(loaded["mem_mb"], rm.boot_profile(CFG)["mem_mb"])

    def test_live_guard_rejects_present_invalid_memory(self):
        guard = ResourceGuard(CFG)
        state = guard.update(snap(float("nan")))
        self.assertEqual((state, guard.mode), ("CRITICAL", "RED"))
        self.assertIn("INVALID_MEM_AVAILABLE", guard.reasons)

    def test_valid_modes_and_hysteresis_unchanged(self):
        self.assertEqual(rm.classify(snap(4000, 30), self.profile)[0], "GREEN")
        self.assertEqual(rm.classify(snap(1200, 30), self.profile)[0], "YELLOW")
        self.assertEqual(rm.classify(snap(900, 30), self.profile)[0], "ORANGE")
        self.assertEqual(rm.classify(snap(400, 30), self.profile)[0], "RED")
        self.assertEqual(rm.classify(snap(1020, 30), self.profile, "ORANGE")[0], "ORANGE")
        self.assertEqual(rm.classify(snap(1100, 30), self.profile, "ORANGE")[0], "YELLOW")


if __name__ == "__main__":
    unittest.main()
