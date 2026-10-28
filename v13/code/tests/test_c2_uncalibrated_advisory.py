"""Uncalibrated C2 native route proposals must not override the scaffold.

Isolated Runtime-source candidate; mocked software only, not native quality evidence.
"""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime


class C2UncalibratedAdvisory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.text = "Hi there, how are you today?"
        self.event = self.r.store.event(self.r.session, self.text)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def route(self, calibration, learned=None):
        r = self.r
        with (patch.object(r.consolidation, "route", return_value=None),
              patch("v13.episodic_route.for_turn", return_value=(None, None)),
              patch.object(r.executive, "control_context",
                           return_value={"packet_id": "synthetic-test"}),
              patch.object(r.executive, "control_admissible",
                           return_value=(True, None)),
              patch.object(r.learner, "propose", return_value=learned),
              patch.object(r.learner, "compare_student_route", return_value=None),
              patch.object(r.learner, "control_calibrate", return_value=calibration),
              patch.object(r.needle, "control", return_value={"route": "detail"}) as native):
            result = r._route(self.text, self.event, time.monotonic() + 10)
        return result, native.call_count

    def test_uncalibrated_native_is_recorded_but_never_overrides_simple(self):
        (route, info), calls = self.route(None)
        self.assertEqual(calls, 1)
        self.assertEqual(route, "simple")
        self.assertEqual(info["source"], "BOOT_SCAFFOLD")
        self.assertEqual(info["native_control"], {"route": "detail"})
        self.assertIs(info["calibrated"], False)
        self.assertIs(info["native_control_rejected"], True)
        self.assertEqual(info["native_control_reason"], "NO_SUPPORTED_FINITE_CALIBRATION")

    def test_supported_finite_calibration_can_admit_native_route(self):
        (route, info), calls = self.route(
            {"in_support": True, "calibrated_confidence": .9})
        self.assertEqual(calls, 1)
        self.assertEqual(route, "detail")
        self.assertEqual(info["source"], "NATIVE_C2_ADVISORY")
        self.assertIs(info["calibrated"], True)
        self.assertNotIn("native_control_rejected", info)

    def test_below_threshold_and_out_of_support_abstain(self):
        for candidate, reason in (
            ({"in_support": True, "calibrated_confidence": .599},
             "BELOW_CALIBRATED_THRESHOLD"),
            ({"in_support": False, "calibrated_confidence": .99},
             "NO_SUPPORTED_FINITE_CALIBRATION"),
        ):
            with self.subTest(candidate=candidate):
                (route, info), calls = self.route(candidate)
                self.assertEqual(calls, 1)
                self.assertEqual(route, "simple")
                self.assertIs(info["native_control_rejected"], True)
                self.assertEqual(info["native_control_reason"], reason)

    def test_nonfinite_or_malformed_calibration_cannot_promote(self):
        bad = (float("nan"), float("inf"), -float("inf"), True, "0.99", -1., 1.01, None)
        for confidence in bad:
            with self.subTest(confidence=repr(confidence)):
                (route, info), _ = self.route(
                    {"in_support": True, "calibrated_confidence": confidence})
                self.assertEqual(route, "simple")
                self.assertIs(info["calibrated"], False)
                self.assertIs(info["native_control_rejected"], True)
        for support in (1, "yes", None):
            with self.subTest(support=support):
                (route, info), _ = self.route(
                    {"in_support": support, "calibrated_confidence": .9})
                self.assertEqual(route, "simple")
                self.assertIs(info["native_control_rejected"], True)

    def test_explicit_approved_external_head_remains_separate(self):
        (route, info), calls = self.route(
            None, learned={"route": "both", "margin": .8})
        self.assertEqual(route, "both")
        self.assertEqual(info["source"], "APPROVED_EXTERNAL_HEAD")
        self.assertEqual(calls, 0)


if __name__ == "__main__":
    unittest.main()
