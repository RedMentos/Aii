"""Run19 test-first: §97.2 resource calibration cannot certify malformed measurements."""
import copy
import math
import tempfile
import unittest
from pathlib import Path

from v13 import resource_modes as rm
from v13.runtime import Runtime

CFG = {"minimum_free_mb": 500, "thermal_limit_c": 45.0}
VALID_RSS = {"B1_DETAIL": 800, "B2_GIST": 600}


class ResourceFiniteCalibration(unittest.TestCase):
    def test_nonfinite_boolean_or_nonpositive_body_rss_rejected(self):
        for bad in (float("inf"), float("-inf"), float("nan"), True, False, 0, -1):
            with self.subTest(value=repr(bad)):
                readings = dict(VALID_RSS, B1_DETAIL=bad)
                with self.assertRaises(ValueError):
                    rm.calibrate(CFG, readings, {"android": True})
        good = rm.calibrate(CFG, VALID_RSS, {"android": True}, clock=lambda: 7.0)
        self.assertEqual(good["status"], "DEVICE_MEASURED")
        self.assertEqual(good["mem_mb"]["YELLOW"], 2110.0)

    def test_thermal_measurements_reject_nonfinite_boolean_and_invalid(self):
        for bad in (float("inf"), float("-inf"), float("nan"), True, False, "hot"):
            with self.subTest(value=repr(bad)):
                thermal = {"RED": 44.0, "ORANGE": 41.0, "YELLOW": 38.0}
                thermal["RED"] = bad
                with self.assertRaises((ValueError, TypeError)):
                    rm.calibrate(CFG, VALID_RSS, {"android": True}, thermal=thermal)
        good = rm.calibrate(CFG, VALID_RSS, {"android": True},
                            thermal={"RED": 44.0, "ORANGE": 41.0, "YELLOW": 38.0})
        self.assertEqual(good["thermal_status"], "DEVICE_MEASURED")

    def test_validation_rejects_corrupted_persisted_thresholds(self):
        for path, key, value in (
            ("mem_mb", "RED", True),
            ("mem_mb", "RED", float("inf")),
            ("mem_mb", "ORANGE", float("nan")),
            ("temp_c", "RED", float("inf")),
            ("temp_c", "RED", True),
            ("rss_mb", "YELLOW", float("inf")),
            ("rss_mb", "YELLOW", True),
        ):
            with self.subTest(path=path, key=key, value=repr(value)):
                p = copy.deepcopy(rm.boot_profile(CFG, {"android": True}))
                if path == "rss_mb":
                    p["rss_mb"] = {"YELLOW": value, "ORANGE": float("inf")}
                else:
                    p[path][key] = value
                with self.assertRaises(ValueError):
                    rm.validate(p)

    def test_corrupted_store_profile_falls_back_to_uncalibrated_boot(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Runtime(Path(tmp))
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                bad = rm.boot_profile(CFG, {"android": False})
                bad["mem_mb"]["RED"] = True  # JSON-persistable but not a measurement
                bad["status"] = "DEVICE_MEASURED"
                r.store.set_state(rm.STATE_KEY, bad)
                loaded = rm.load_profile(r.store, CFG)
                self.assertEqual(loaded["status"], "UNCALIBRATED")
                self.assertEqual(loaded["mem_mb"]["RED"], 500.0)
            finally:
                r.close()

    def test_only_exact_android_true_can_claim_redmi_measurement(self):
        for android in ("false", "true", 1, None, False):
            with self.subTest(android=repr(android)):
                device = {"android": android}
                boot = rm.boot_profile(CFG, device)
                self.assertNotEqual(boot["rss_status"], "BOOT_REDMI_TARGET")
                p = rm.calibrate(CFG, VALID_RSS, device)
                self.assertEqual(p["status"], "HOST_MEASURED_NOT_REDMI")
                self.assertEqual(p["thermal_status"], "BOOT_UNMEASURED")
        self.assertEqual(rm.calibrate(CFG, VALID_RSS, {"android": True})["status"],
                         "DEVICE_MEASURED")


if __name__ == "__main__":
    unittest.main()
