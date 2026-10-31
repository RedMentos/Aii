"""Run41 C2/JEF advisory pure software contract; no live runtime authority."""
import copy
import unittest

from v13.common import Cancelled
from v13.c2_monotone_route_shadow import choose, NEGATIVE_GATES
from v13.c2_route_admission_shadow import evaluate as frozen_admission
from v13.control_calibration_worker import observation


def control(route="both", **changes):
    c = {"success": True, "validation": {"negation": False, "ungrounded": False},
         "confidence": .91,
         "function_calls": [{"name": "select_processing", "arguments": {"route": route}}]}
    c.update(changes)
    return c


def approved(c, confidence=.9):
    return observation(c) | {"in_support": True,
                             "calibrated_confidence": confidence,
                             "route_observation_count": 8,
                             "calibration_scope": "HELD_OUT_NATIVE_ROUTE_AGREEMENT_ONLY",
                             "semantic_truth_authority": False}


def select(scaffold="detail", c=None, **overrides):
    c = control() if c is None else c
    kwargs = dict(effort_band="FOCAL_TARGETED", resource_wake_ceiling="both",
                  executive_admissible=True, source_bound=True)
    try:
        kwargs["calibration"] = approved(c)
    except (ValueError, TypeError, KeyError, OverflowError):
        kwargs["calibration"] = None
    kwargs.update(overrides)
    return choose(scaffold, c, **kwargs)


class MonotoneC2Shadow(unittest.TestCase):
    def test_detail_to_both_only_when_two_body_allowed(self):
        good = select()
        self.assertEqual((good["selected_route"], good["changed"], good["authority"]),
                         ("both", True, "SHADOW_ONLY"))
        self.assertEqual(select(effort_band="C_NATIVE_ONE_BODY")["reason"],
                         "EFFORT_OR_RESOURCE_CEILING")
        self.assertEqual(select(resource_wake_ceiling="one")["selected_route"], "detail")

    def test_gist_to_both_and_simple_to_one(self):
        self.assertTrue(select("gist")["changed"])
        self.assertEqual(select("simple", control("detail"),
                                effort_band="C_NATIVE_ONE_BODY")["selected_route"], "detail")
        self.assertEqual(select("simple", control("gist"),
                                effort_band="C_NATIVE_ONE_BODY")["selected_route"], "gist")

    def test_direct_or_no_resource_denies_all_body_upgrades(self):
        self.assertEqual(select("simple", control("detail"),
                                effort_band="DIRECT_C_NATIVE")["reason"],
                         "EFFORT_OR_RESOURCE_CEILING")
        self.assertEqual(select("simple", control("both"),
                                resource_wake_ceiling="none")["selected_route"], "simple")

    def test_no_demotion_lateral_or_both_downroute(self):
        self.assertEqual(select("detail", control("gist"))["reason"],
                         "DEMOTION_OR_LATERAL_REFUSED")
        self.assertEqual(select("gist", control("detail"))["selected_route"], "gist")
        self.assertEqual(select("both", control("simple"))["selected_route"], "both")
        self.assertEqual(select("both", control("both"))["reason"], "SAME_ROUTE")

    def test_exactly_one_native_select_processing_required(self):
        self.assertEqual(select(c=control(function_calls=[]))["reason"],
                         "NOT_ONE_NATIVE_SELECT_PROCESSING")
        calls = control()["function_calls"] * 2
        self.assertEqual(select(c=control(function_calls=calls))["reason"],
                         "NOT_ONE_NATIVE_SELECT_PROCESSING")
        self.assertEqual(select(c=control(function_calls=[{"name": "diagnostic", "arguments": {"route": "both"}}]))["reason"],
                         "NOT_ONE_NATIVE_SELECT_PROCESSING")
        self.assertEqual(select(c=control(function_calls="both"))["reason"],
                         "NOT_ONE_NATIVE_SELECT_PROCESSING")

    def test_nonfinite_boolean_negation_ungrounded_and_unsuccessful_rejected(self):
        for bad in (control(confidence=float("nan")), control(confidence=True),
                    control(confidence=float("inf")),
                    control(validation={"negation": True}),
                    control(validation={"ungrounded": True}),
                    control(success=False)):
            with self.subTest(bad=repr(bad)):
                r = select(c=bad)
                self.assertEqual(r["reason"], "NATIVE_VALIDATION_FAIL")
                self.assertFalse(r["changed"])

    def test_calibration_must_match_exact_native_observation(self):
        c = control()
        base = approved(c)
        self.assertTrue(select(c=c, calibration=base)["changed"])
        for changes in ({"route": "detail"}, {"raw_confidence": .5},
                        {"proposal_count": 2}, {"ambiguous": True}):
            with self.subTest(changes=changes):
                self.assertEqual(select(c=c, calibration=base | changes)["reason"],
                                 "CALIBRATION_SOURCE_MISMATCH")
        self.assertEqual(select(c=c, calibration=None)["reason"],
                         "NO_APPROVED_CALIBRATION")

    def test_calibration_scope_support_and_threshold(self):
        c = control()
        base = approved(c)
        for changes in ({"in_support": False}, {"calibration_scope": "OTHER"},
                        {"semantic_truth_authority": True},
                        {"route_observation_count": 2},
                        {"route_observation_count": True},
                        {"calibrated_confidence": None},
                        {"calibrated_confidence": False},
                        {"calibrated_confidence": float("nan")},
                        {"calibrated_confidence": float("inf")},
                        {"calibrated_confidence": 1.01},
                        {"calibrated_confidence": 10**1000}):
            with self.subTest(changes=repr(changes)):
                self.assertEqual(select(c=c, calibration=base | changes)["reason"],
                                 "CALIBRATION_UNSUPPORTED")
        self.assertEqual(select(c=c, calibration=base | {"calibrated_confidence": .5999})["reason"],
                         "CALIBRATION_BELOW_THRESHOLD")
        self.assertTrue(select(c=c, calibration=base | {"calibrated_confidence": .6})["changed"])

    def test_existing_simple_shadow_calibration_parity(self):
        c = control("detail")
        cal = approved(c)
        old = frozen_admission("simple", c, cal)
        self.assertTrue(old["would_admit"])
        self.assertEqual(select("simple", c, calibration=cal)["selected_route"],
                         old["candidate_route"])
        for invalid in (None, cal | {"raw_confidence": .7},
                        cal | {"route_observation_count": 1}):
            self.assertFalse(frozen_admission("simple", c, invalid)["would_admit"])
            self.assertFalse(select("simple", c, calibration=invalid)["changed"])

    def test_executive_source_guards_and_cancellation(self):
        self.assertEqual(select(source_bound=False)["reason"], "SOURCE_UNBOUND")
        self.assertEqual(select(executive_admissible=False)["reason"], "EXECUTIVE_ABSTAIN")
        with self.assertRaises(Cancelled):
            select(cancelled=True)
        for kwargs in ({"source_bound": 1}, {"executive_admissible": "yes"},
                       {"cancelled": None}):
            with self.assertRaisesRegex(ValueError, "UNTYPED_GUARD"):
                select(**kwargs)

    def test_input_immutability_and_negative_gates(self):
        c = control()
        cal = approved(c)
        before_c, before_cal = copy.deepcopy(c), copy.deepcopy(cal)
        r = select(c=c, calibration=cal)
        self.assertEqual(c, before_c)
        self.assertEqual(cal, before_cal)
        self.assertEqual(r["negative_gates"], NEGATIVE_GATES)
        r["negative_gates"]["step2"] = "PASS"
        self.assertEqual(NEGATIVE_GATES["step2"], "UTILITY_FAIL")

    def test_unknown_route_budget_fail_closed(self):
        for kwargs in ({"scaffold": "tool"}, {"effort_band": "unlimited"},
                       {"resource_wake_ceiling": "unlimited"}):
            with self.assertRaisesRegex(ValueError, "ROUTE_OR_BUDGET_UNKNOWN"):
                select(**kwargs)


if __name__ == "__main__":
    unittest.main()
