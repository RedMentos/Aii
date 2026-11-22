"""Run77 quote-provenance auditor: synthetic only, never a native result."""
import copy
import unittest

from scripts import jef_b1b2_context_fixture_797 as f
from scripts import run77_b2_quote_provenance_audit as audit
from tests.test_run77_forensic_diagnostic import synthetic_report


def report_with_full_refs():
    report = synthetic_report()
    for i, fixture in enumerate(f.fixtures()):
        row = report["rows"][2 * i]
        for kind in ("prior", "current"):
            ref = row[kind + "_source_ref"]
            ref.update(char_start=0, char_end=len(fixture[kind]),
                       modality="text")
    return report


def current_b2(report, fixture_index=0):
    return next(e for e in report["rows"][fixture_index * 2]["offers"]
                if e["role"] == "B2_GIST" and e["phase"] == "current")["offer"]


def inject_prior_quote(report, fixture_index=0, *, whole=False, wide=0):
    fixture = f.fixtures()[fixture_index]
    prior = fixture["prior"]
    phrase = "Maximum budget: " + str(f.TABLE[fixture_index][1]) + " credits."
    start = 0 if whole else prior.index(phrase)
    end = len(prior) if whole else start + len(phrase)
    ref = dict(report["rows"][fixture_index * 2]["prior_source_ref"],
               char_start=start, char_end=end)
    offer = current_b2(report, fixture_index)
    offer["evidence_refs"] = [ref]
    offer["offer"]["quotes"] = [phrase]
    offer["quote_context_chars"] = wide
    return ref


class B2QuoteProvenanceTests(unittest.TestCase):
    def test_zero_evidence_is_valid_negative_observation(self):
        result = audit.audit_report(report_with_full_refs())
        self.assertEqual(result["status"],
                         "B2_QUOTE_PROVENANCE_DIAGNOSTIC_COMPLETE_SHADOW")
        self.assertEqual(result["examined_b2_with_prior_current"], 6)
        self.assertEqual(result["verified_prior_refs"], 0)
        self.assertEqual(len(result["missing_prior_projects"]), 6)
        self.assertFalse(result["native_utility_proven"])
        self.assertEqual(result["delivery_authority"], 0)

    def test_exact_prior_quote_and_current_quote_separated(self):
        report = report_with_full_refs()
        inject_prior_quote(report)
        current = f.fixtures()[0]["current"]
        phrase = "Option A: budget 160 credits"
        start = current.index(phrase)
        offer = current_b2(report)
        offer["evidence_refs"].append(dict(
            report["rows"][0]["current_source_ref"],
            char_start=start, char_end=start + len(phrase)))
        offer["offer"]["quotes"].append(phrase)
        result = audit.audit_report(report)
        self.assertEqual(result["status"],
                         "B2_QUOTE_PROVENANCE_DIAGNOSTIC_COMPLETE_SHADOW")
        self.assertEqual(result["verified_prior_refs"], 1)
        self.assertEqual(result["verified_current_refs"], 1)
        self.assertEqual(result["verified_prior_projects"], ["Alder"])

    def test_full_prior_span_is_only_pointer_if_bounded_and_quoted(self):
        report = report_with_full_refs()
        inject_prior_quote(report, whole=True, wide=200)
        result = audit.audit_report(report)
        self.assertEqual(result["verified_prior_refs"], 1)
        self.assertEqual(result["findings"], [])
        offer = current_b2(report)
        offer["quote_context_chars"] = 0
        result = audit.audit_report(report)
        self.assertIn("QUOTE_NOT_BOUND_TO_SPAN_RED",
                      [e["code"] for e in result["findings"]])

    def test_frozen_run52_400_character_pointer_is_accepted(self):
        report = report_with_full_refs()
        inject_prior_quote(report, whole=True, wide=400)
        result = audit.audit_report(report)
        self.assertEqual(result["status"],
                         "B2_QUOTE_PROVENANCE_DIAGNOSTIC_COMPLETE_SHADOW")
        self.assertEqual(result["verified_prior_refs"], 1)
        self.assertEqual(result["findings"], [])

    def test_unquoted_full_source_cannot_be_counted(self):
        report = report_with_full_refs()
        inject_prior_quote(report, whole=True, wide=200)
        current_b2(report)["offer"]["quotes"] = ["A fabricated quote"]
        result = audit.audit_report(report)
        self.assertEqual(result["verified_prior_refs"], 0)
        self.assertEqual(result["status"], "B2_QUOTE_PROVENANCE_DIAGNOSTIC_RED")

    def test_foreign_source_and_wrong_hash_rejected(self):
        report = report_with_full_refs()
        ref = inject_prior_quote(report)
        ref["source_id"] = "src_foreign"
        result = audit.audit_report(report)
        self.assertIn("FOREIGN_SOURCE_RED",
                      [e["code"] for e in result["findings"]])
        ref["source_id"] = report["rows"][0]["prior_source_ref"]["source_id"]
        ref["sha256"] = "0" * 64
        result = audit.audit_report(report)
        self.assertIn("SOURCE_SPAN_OR_HASH_RED",
                      [e["code"] for e in result["findings"]])

    def test_offset_tamper_and_boolean_index_fail(self):
        report = report_with_full_refs()
        ref = inject_prior_quote(report)
        for start in (-1, True, len(f.fixtures()[0]["prior"])):
            with self.subTest(start=start):
                ref["char_start"] = start
                result = audit.audit_report(report)
                self.assertIn("SOURCE_SPAN_OR_HASH_RED",
                              [e["code"] for e in result["findings"]])

    def test_quote_width_cannot_be_forged(self):
        report = report_with_full_refs()
        inject_prior_quote(report, whole=True, wide=200)
        for wide in (True, -1, 401, "400"):
            with self.subTest(wide=wide):
                current_b2(report)["quote_context_chars"] = wide
                result = audit.audit_report(report)
                self.assertIn("QUOTE_OR_POINTER_SHAPE_RED",
                              [e["code"] for e in result["findings"]])

    def test_identity_missing_rows_and_cross_arm_swap_red(self):
        report = report_with_full_refs()
        report["rows"] = report["rows"][:-1]
        self.assertIn("ROW_COUNT_RED",
                      [e["code"] for e in audit.audit_report(report)["findings"]])
        report = report_with_full_refs()
        report["rows"][0], report["rows"][1] = report["rows"][1], report["rows"][0]
        self.assertIn("ROW_IDENTITY_RED",
                      [e["code"] for e in audit.audit_report(report)["findings"]])

    def test_malformed_quote_and_duplicated_b2_entry_fail(self):
        report = report_with_full_refs()
        inject_prior_quote(report)
        offer = current_b2(report)
        offer["offer"]["quotes"] = [42]
        self.assertIn("QUOTE_OR_POINTER_SHAPE_RED",
                      [e["code"] for e in audit.audit_report(report)["findings"]])
        report = report_with_full_refs()
        row = report["rows"][0]
        b2 = next(e for e in row["offers"]
                  if e["role"] == "B2_GIST" and e["phase"] == "current")
        row["offers"].append(copy.deepcopy(b2))
        self.assertIn("B2_CURRENT_OFFER_COUNT_RED",
                      [e["code"] for e in audit.audit_report(report)["findings"]])


if __name__ == "__main__":
    unittest.main()
