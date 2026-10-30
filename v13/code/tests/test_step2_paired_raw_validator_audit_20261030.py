"""Software-only independent scorer and original raw-archive tamper checks."""
import tempfile
import unittest
from pathlib import Path
from step2_paired_raw_validator_audit import (
    _number_claims, semantic_diagnostic, audit_zip)

F = {"project": "Vega", "budget": 145,
     "a": "Amber", "a_cost": 95, "b": "Cobalt", "b_cost": 125}


class ReadOnlyNativePilotAuditTests(unittest.TestCase):
    def test_leaves_and_inherited_remaining_premise(self):
        for text in (
            "Option Amber leaves 50 Euro; Option Cobalt leaves 20 Euro.",
            "The remaining budget for Option Amber is 50 Euro, and for Option Cobalt it is 20 Euro.",
            "Amber has a remaining budget of 50 Euro; Cobalt has a remaining budget of 20 Euro.",
        ):
            with self.subTest(text=text):
                got = semantic_diagnostic(F, text)
                self.assertTrue(got["a"]["correct"])
                self.assertTrue(got["b"]["correct"])

    def test_contradictory_same_option_vetoes_correct_claim(self):
        got = semantic_diagnostic(F,
            "Amber leaves 50 Euro; Amber: 95 Euro - 50 Euro = 45 Euro remaining. "
            "Cobalt leaves 20 Euro; Cobalt: 125 Euro - 20 Euro = 105 Euro remaining.")
        self.assertEqual(got["a"]["status"], "CONTRADICTORY")
        self.assertEqual(got["b"]["status"], "CONTRADICTORY")
        self.assertEqual(got["a"]["claims"], [45, 50])
        self.assertEqual(got["b"]["claims"], [20, 105])

    def test_costs_or_wrong_option_do_not_become_remainders(self):
        for text in (
            "Option Amber costs 95 Euro. Option Cobalt costs 125 Euro.",
            "Option Amber: €150 (€45 more than Cobalt).",
            "Option Cobalt leaves 50 Euro; Amber costs 95 Euro.",
        ):
            with self.subTest(text=text):
                self.assertFalse(semantic_diagnostic(F, text)["a"]["correct"])

    def test_wrong_and_missing_are_not_positive(self):
        got = semantic_diagnostic(F, "Amber leaves 40 Euro; Cobalt takes 1 day.")
        self.assertEqual(got["a"]["status"], "WRONG")
        self.assertEqual(got["b"]["status"], "MISSING")

    def test_foreign_label_cannot_cross_option_boundary(self):
        got = _number_claims(
            "Amber costs 95 Euro, Cobalt leaves 20 Euro.", "Amber", "Cobalt")
        self.assertEqual(got, [])

    def test_arbitrary_archive_rejected_before_any_scoring(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "not-original.zip"
            p.write_bytes(b"untrusted synthetic archive")
            with self.assertRaisesRegex(ValueError, "ORIGINAL_ZIP_SHA_RED"):
                audit_zip(p)


if __name__ == "__main__":
    unittest.main()
