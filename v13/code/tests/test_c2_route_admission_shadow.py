"""Source-bound C2 route admission SHADOW tests; no Runtime or native model."""
import copy
import unittest

from v13 import c2_route_admission_shadow as admission
from v13.control_calibration_worker import observation


def native(route="detail", confidence=.82):
    return {
        "success": True, "confidence": confidence,
        "validation": {"negation": False, "ungrounded": []},
        "function_calls": [{"name": "select_processing",
                            "arguments": {"route": route}}],
    }


def calibration(control, confidence=.9):
    return observation(control) | {
        "in_support": True, "calibrated_confidence": confidence,
        "route_observation_count": 8,
        "calibration_scope": admission.CALIBRATION_SCOPE,
        "semantic_truth_authority": False,
    }


class C2SourceBoundShadow(unittest.TestCase):
    def assert_no_authority(self, result):
        self.assertEqual(result["authority"], "SHADOW_ONLY_NO_RUNTIME_ROUTE")
        self.assertIs(result["applied"], False)
        self.assertEqual(result["age_authority"], 0)
        self.assertIs(result["model_called"], False)
        self.assertIs(result["weight_updates"], False)

    def test_valid_source_bound_calibration_only_proposes_without_applying(self):
        raw = native()
        bound = calibration(raw)
        before_raw, before_bound = copy.deepcopy(raw), copy.deepcopy(bound)
        result = admission.evaluate("simple", raw, bound)
        self.assertTrue(result["would_admit"])
        self.assertEqual(result["candidate_route"], "detail")
        self.assertEqual(result["native_route"], "detail")
        self.assertEqual(result["reason"], "ELIGIBLE_SHADOW_ONLY")
        self.assert_no_authority(result)
        self.assertEqual(raw, before_raw)
        self.assertEqual(bound, before_bound)

    def test_no_calibration_never_grants_route_authority(self):
        result = admission.evaluate("simple", native(), None)
        self.assertFalse(result["would_admit"])
        self.assertEqual(result["reason"], "NO_APPROVED_CALIBRATION")
        self.assertIsNone(result["candidate_route"])
        self.assert_no_authority(result)

    def test_native_tool_must_be_valid_single_select_processing(self):
        cases = [
            None, {}, {"route": "detail"},
            native(confidence=float("nan")),
            native() | {"success": False},
            native() | {"validation": {"negation": True}},
            native() | {"function_calls": [{"name": "foreign",
                                           "arguments": {"route": "detail"}}]},
            native() | {"function_calls": [
                {"name": "select_processing", "arguments": {"route": "detail"}},
                {"name": "select_processing", "arguments": {"route": "both"}}]},
            native() | {"function_calls": [
                {"name": "foreign", "arguments": {"route": "both"}},
                {"name": "select_processing", "arguments": {"route": "detail"}}]},
        ]
        for raw in cases:
            with self.subTest(raw=repr(raw)[:80]):
                result = admission.evaluate("simple", raw, calibration(native()))
                self.assertFalse(result["would_admit"])
                self.assertEqual(result["reason"], "INVALID_NATIVE_CONTROL")
                self.assert_no_authority(result)

    def test_foreign_nested_route_never_replaces_validated_route(self):
        raw = native()
        raw["route"] = "both"
        raw["diagnostic"] = {"route": "gist"}
        result = admission.evaluate("simple", raw, calibration(raw))
        self.assertTrue(result["would_admit"])
        self.assertEqual(result["candidate_route"], "detail")
        self.assert_no_authority(result)

    def test_calibration_must_match_same_native_observation(self):
        raw = native()
        for changes in (
            {"route": "both"}, {"raw_confidence": .7},
            {"proposal_count": 2}, {"ambiguous": True},
        ):
            with self.subTest(changes=changes):
                bound = calibration(raw) | changes
                result = admission.evaluate("simple", raw, bound)
                self.assertFalse(result["would_admit"])
                self.assertEqual(result["reason"], "CALIBRATION_SOURCE_MISMATCH")

    def test_unsupported_or_malformed_calibration_refuses(self):
        raw = native()
        bad = (
            {"in_support": False}, {"in_support": "yes"},
            {"calibration_scope": "OTHER"}, {"semantic_truth_authority": True},
            {"route_observation_count": 2}, {"route_observation_count": True},
            {"calibrated_confidence": float("nan")},
            {"calibrated_confidence": float("inf")},
            {"calibrated_confidence": -1.},
            {"calibrated_confidence": 1.1},
            {"calibrated_confidence": True},
            {"calibrated_confidence": "0.9"},
        )
        for changes in bad:
            with self.subTest(changes=repr(changes)):
                result = admission.evaluate("simple", raw, calibration(raw) | changes)
                self.assertFalse(result["would_admit"])
                self.assertEqual(result["reason"], "UNSUPPORTED_CALIBRATION")
                self.assert_no_authority(result)

    def test_threshold_and_non_simple_scaffold_abstain(self):
        raw = native()
        low = admission.evaluate("simple", raw, calibration(raw, .599))
        self.assertFalse(low["would_admit"])
        self.assertEqual(low["reason"], "BELOW_CALIBRATED_THRESHOLD")
        for route in ("detail", "gist", "both"):
            with self.subTest(route=route):
                result = admission.evaluate(route, raw, calibration(raw))
                self.assertFalse(result["would_admit"])
                self.assertEqual(result["reason"], "SCAFFOLD_NOT_SIMPLE")
                self.assert_no_authority(result)

    def test_invalid_scaffold_route_is_a_programming_error(self):
        for route in ("AUTO", "native", None, True):
            with self.subTest(route=route):
                with self.assertRaises(ValueError):
                    admission.evaluate(route, native(), calibration(native()))


if __name__ == "__main__":
    unittest.main()
