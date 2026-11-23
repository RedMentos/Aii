"""Run117 synthetic software-only source provenance/abstention regressions."""
from __future__ import annotations

import hashlib
import unittest

from scripts import run117_step2_rule_source_candidate as candidate
from scripts import run109_step2_fresh_fixtures as corpus


class Run117ExactRuleSpan(unittest.TestCase):
    def test_six_fresh_fixtures_latest_exact_vs_240(self):
        report = candidate.evaluate()
        self.assertEqual(report["candidate_covered"], 6)
        self.assertEqual(report["legacy_covered"], 3)
        self.assertEqual(report["native_calls"], 0)
        self.assertFalse(report["canonical_gate_pass"])
        self.assertFalse(report["whole_system_complete"])
        self.assertEqual(report["fixture_sha256"], candidate.FIXTURE_SHA256)
        for row in report["rows"]:
            self.assertTrue(row["exact_substring"])
            self.assertFalse(row["candidate"]["semantic_authority"])

    def test_long_rules_beyond_excerpt(self):
        for f in corpus.fixtures()[:3]:
            with self.assertRaisesRegex(ValueError, "NO_COMPLETE_SOURCE_RULE"):
                candidate.select([s[:240] for s in f["history"]], f["id"])
            result = candidate.select(f["history"], f["id"])
            self.assertGreaterEqual(result["char_start"], 240)
            self.assertEqual(result["source_index"], 0)

    def test_revised_latest_wins_without_using_oracle(self):
        for f in corpus.fixtures()[3:]:
            result = candidate.select(f["history"], f["id"])
            self.assertEqual(result["source_index"], 1)
            self.assertIn("Budget " + str(f["rules"]["budget"]) + " euros",
                          result["text"])
            self.assertNotIn("Budget " + str(f["old_rules"]["budget"]) + " euros",
                             result["text"])

    def test_exact_source_and_span_hashes(self):
        f = corpus.fixtures()[0]
        result = candidate.select(f["history"], f["id"])
        source = f["history"][result["source_index"]]
        text = source[result["char_start"]:result["char_end"]]
        self.assertEqual(text, result["text"])
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),
                         result["source_sha256"])
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),
                         result["span_sha256"])

    def test_wrong_project_and_near_prefix_refused(self):
        with self.assertRaisesRegex(ValueError, "NO_COMPLETE_SOURCE_RULE"):
            candidate.select(["Project AtlasX. Budget 9 euros. Deadline 1 days. "
                              "Local-only requirement: true."], "Atlas")
        with self.assertRaisesRegex(ValueError, "NO_COMPLETE_SOURCE_RULE"):
            candidate.select(["Project Zenith. Budget 9 euros. Deadline 1 days. "
                              "Local-only requirement: true."], "Atlas")

    def test_cross_project_rule_inside_same_source_refused(self):
        source = ("Project Atlas meeting. Project Zenith. Budget 130 euros. "
                  "Deadline 6 days. Local-only requirement: true.")
        with self.assertRaisesRegex(ValueError, "CROSS_PROJECT_SOURCE_AMBIGUOUS"):
            candidate.select([source], "Atlas")

    def test_incomplete_later_revision_fails_closed(self):
        sources = ["Project Atlas. Budget 130 euros. Deadline 6 days. "
                   "Local-only requirement: true.",
                   "Project Atlas revision: Budget 50 euros, other rules pending."]
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_LATER_RULE_SOURCE"):
            candidate.select(sources, "Atlas")

    def test_same_source_two_complete_rules_fails_closed(self):
        sources = ["Project Atlas. Budget 130 euros. Deadline 6 days. "
                   "Local-only requirement: true. Budget 80 euros. "
                   "Deadline 2 days. Local-only requirement: false."]
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_SAME_SOURCE_REVISIONS"):
            candidate.select(sources, "Atlas")

    def test_same_source_extra_partial_rule_fails_closed(self):
        sources = ["Project Atlas. Budget 130 euros. Deadline 6 days. "
                   "Local-only requirement: true. Budget 80 euros."]
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_EXTRA_RULE_FIELDS"):
            candidate.select(sources, "Atlas")

    def test_missing_fields_and_no_rules_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_LATER_RULE_SOURCE"):
            candidate.select(["Project Atlas. Budget 130 euros."], "Atlas")
        with self.assertRaisesRegex(ValueError, "NO_COMPLETE_SOURCE_RULE"):
            candidate.select(["Project Atlas. Supplier discussion only."], "Atlas")

    def test_reject_bad_project_cap_and_source_types(self):
        good = ["Project Atlas. Budget 130 euros. Deadline 6 days. "
                "Local-only requirement: true."]
        for name in ("", "../Atlas", "Atlas Other", "Atlas/Zenith"):
            with self.assertRaisesRegex(ValueError, "INVALID_PROJECT"):
                candidate.select(good, name)
        for cap in (0, -1, 201, True):
            with self.assertRaisesRegex(ValueError, "INVALID_CAP"):
                candidate.select(good, "Atlas", cap)
        with self.assertRaisesRegex(ValueError, "INVALID_SOURCES"):
            candidate.select([None], "Atlas")

    def test_cap_below_span_refused(self):
        with self.assertRaisesRegex(ValueError, "RULE_SPAN_OVER_CAP"):
            candidate.select(["Project Atlas. Budget 130 euros. Deadline 6 days. "
                              "Local-only requirement: true."], "Atlas", 10)


if __name__ == "__main__":
    unittest.main()
