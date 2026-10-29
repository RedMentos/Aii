"""WP-N9 Self/World attribution: bool is not a numeric observation (software only)."""
import unittest
from v13 import selfmodel as S


def cor(pred):
    return {
        "action_id": "act",
        "issued_at": 100.,
        "window_s": 10.,
        "affected": ["duration_s"],
        "predicted_observations": [dict(pred, channel="duration_s")],
    }


def observe(pred, value):
    return S.attribute([cor(pred)], {"channel": "duration_s", "value": value, "t": 105.})


class BoolNumberAttributionTests(unittest.TestCase):
    def test_numeric_prediction_boolean_true_is_not_exact_self(self):
        p = {"value": 1.0, "tolerance": 0.0}
        matched, residual = S._match(p, True)
        self.assertFalse(matched)
        self.assertEqual(residual, {"expected": 1.0, "actual": True})
        result = observe(p, True)
        self.assertEqual(result["class"], "MIXED")
        self.assertEqual(result["reason"], "partial_or_mismatched_outcome")
        self.assertEqual(result["residual"], residual)

    def test_boolean_prediction_numeric_zero_is_not_self(self):
        p = {"value": False}
        matched, residual = S._match(p, 0)
        self.assertFalse(matched)
        self.assertEqual(residual, {"expected": False, "actual": 0})
        self.assertEqual(observe(p, 0)["class"], "MIXED")

    def test_boolean_prediction_numeric_one_is_not_self(self):
        p = {"value": True}
        self.assertFalse(S._match(p, 1)[0])
        self.assertEqual(observe(p, 1)["class"], "MIXED")

    def test_numeric_prediction_boolean_false_is_not_self(self):
        p = {"value": 0.0, "tolerance": 0.0}
        self.assertFalse(S._match(p, False)[0])
        self.assertEqual(observe(p, False)["class"], "MIXED")

    def test_boolean_to_boolean_still_matches(self):
        p = {"value": True}
        self.assertEqual(S._match(p, True), (True, None))
        self.assertEqual(observe(p, True)["class"], "SELF")
        self.assertFalse(S._match(p, False)[0])

    def test_numeric_to_numeric_keeps_tolerance_and_residual(self):
        p = {"value": 1.0, "tolerance": 0.25}
        self.assertEqual(S._match(p, 1), (True, 0.0))
        self.assertTrue(S._match(p, 1.2)[0])
        self.assertAlmostEqual(S._match(p, 1.2)[1], 0.2)
        self.assertEqual(observe(p, 1)["class"], "SELF")

    def test_wildcard_boolean_still_matches(self):
        self.assertEqual(S._match({"value": "*"}, True), (True, None))
        self.assertEqual(observe({"value": "*"}, False)["class"], "SELF")

    def test_type_mismatch_not_zero_numeric_residual(self):
        for expected, observed in ((True, 1), (False, 0), (1., True), (0., False)):
            with self.subTest(expected=expected, observed=observed):
                match, residual = S._match({"value": expected, "tolerance": 0.}, observed)
                self.assertFalse(match)
                self.assertIsInstance(residual, dict)
                self.assertNotEqual(observe({"value": expected, "tolerance": 0.}, observed)["class"], "SELF")


if __name__ == "__main__":
    unittest.main()
