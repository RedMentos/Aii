"""C2 archived hybrid must never treat an unvalidated native route as usable."""
import unittest

from scripts import c2_route96_hybrid_archived_20261030 as h
from tests.test_c2_route96_hybrid_archived_20261030 import rows


class C2ArchivedValidatedAdmission(unittest.TestCase):
    def test_unvalidated_high_confidence_route_falls_back_to_scaffold(self):
        native, scaffold = rows(native_correct=True)
        native[0]["validated"] = False
        native[0]["confidence"] = 1.0
        predicted, used_native = h.predict(native[0], scaffold[0], 0.)
        self.assertEqual(predicted, scaffold[0]["pred"])
        self.assertFalse(used_native)
        # Crossvalidation may still choose validated native rows; the
        # unvalidated row itself must never be selected at any threshold.
        for threshold in h.THRESHOLDS:
            _, selected = h.predict(native[0], scaffold[0], threshold)
            self.assertFalse(selected)

    def test_validated_is_exact_boolean_not_truthy_or_missing(self):
        native, scaffold = rows()
        for value in ("true", 1, None):
            with self.subTest(value=value):
                native[0]["validated"] = value
                with self.assertRaises(ValueError):
                    h.validate(native, scaffold)
        del native[0]["validated"]
        with self.assertRaises(ValueError):
            h.validate(native, scaffold)

    def test_validated_true_requires_an_actual_native_route(self):
        native, scaffold = rows()
        native[0]["pred"] = None
        native[0]["validated"] = True
        with self.assertRaises(ValueError):
            h.validate(native, scaffold)

    def test_invalid_native_with_null_route_still_falls_back(self):
        native, scaffold = rows()
        native[0].update(pred=None, confidence=None, validated=False)
        h.validate(native, scaffold)
        self.assertEqual(h.predict(native[0], scaffold[0], 0.),
                         (scaffold[0]["pred"], False))


if __name__ == "__main__":
    unittest.main()
