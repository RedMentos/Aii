"""Run118 synthetic cap24 source-ref binding tests; no model/native calls."""
from __future__ import annotations

import hashlib
import unittest

from scripts import run109_step2_fresh_fixtures as corpus
from scripts import run118_step2_rule_pointer_choice_candidate as candidate


class Run118PointerChoiceCandidate(unittest.TestCase):
    def records(self, fixture):
        history = [candidate.make_record(s, fixture["id"] + "-h" + str(i))
                   for i, s in enumerate(fixture["history"])]
        current = candidate.make_record(
            fixture["current"], fixture["id"] + "-current")
        return current, history

    def test_all_six_frozen_fixtures_prior_choice_coverage(self):
        report = candidate.evaluate()
        self.assertEqual(report["candidate_covered"], 6)
        self.assertLess(report["legacy_covered"], 6)
        self.assertEqual(report["fixture_sha256"], candidate.FIXTURE_SHA256)
        self.assertEqual(report["native_calls"], 0)
        self.assertFalse(report["canonical_gate_pass"])
        for row in report["rows"]:
            self.assertGreaterEqual(row["prior_choice_count"], 3)
            self.assertTrue(row["candidate_covered"])

    def test_choice_offsets_and_sha_bind_original_source(self):
        f = corpus.fixtures()[0]
        current, history = self.records(f)
        result = candidate.build(current, history, f["id"])
        sources = {r["source_ref"]["source_id"]: r for r in history + [current]}
        for choice in result["choices"]:
            ref = choice["source_ref"]
            source = sources[ref["source_id"]]["text"]
            self.assertEqual(source[ref["char_start"]:ref["char_end"]],
                             choice["text"])
            self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),
                             ref["sha256"])
            self.assertFalse(choice["semantic_authority"])

    def test_prior_first_survives_current_40_sentences_cap24(self):
        f = corpus.fixtures()[0]
        _, history = self.records(f)
        current = candidate.make_record(
            "Project Atlas. " + "Sentence filler. " * 40, "atlas-long-current")
        result = candidate.build(current, history, "Atlas", cap=24)
        self.assertTrue(result["candidate_covered"])
        self.assertFalse(result["legacy_covered"])
        self.assertEqual(result["cap"], 24)
        self.assertLessEqual(len(result["choices"]), 24)

    def test_revised_latest_source_chosen_not_superseded(self):
        for f in corpus.fixtures()[3:]:
            current, history = self.records(f)
            result = candidate.build(current, history, f["id"])
            self.assertEqual(result["selected_prior_source_index"], 1)
            prior = [c for c in result["choices"]
                     if c["kind"] == "PRIOR_RULE_SOURCE"]
            self.assertTrue(all(c["source_ref"]["source_id"] == f["id"] + "-h1"
                                for c in prior))
            self.assertTrue(any(
                "Budget " + str(f["rules"]["budget"]) in c["text"]
                for c in prior))

    def test_tampered_source_sha_refused(self):
        f = corpus.fixtures()[0]
        current, history = self.records(f)
        history[0]["source_ref"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_REF_BINDING_RED"):
            candidate.build(current, history, f["id"])

    def test_tampered_source_bounds_refused(self):
        f = corpus.fixtures()[0]
        current, history = self.records(f)
        history[0]["source_ref"]["char_end"] -= 1
        with self.assertRaisesRegex(ValueError, "SOURCE_REF_BINDING_RED"):
            candidate.build(current, history, f["id"])

    def test_duplicate_source_identity_refused(self):
        f = corpus.fixtures()[0]
        current, history = self.records(f)
        current["source_ref"]["source_id"] = history[0]["source_ref"]["source_id"]
        with self.assertRaisesRegex(ValueError, "DUPLICATE_SOURCE_ID"):
            candidate.build(current, history, f["id"])

    def test_wrong_current_project_refused(self):
        f = corpus.fixtures()[0]
        _, history = self.records(f)
        current = candidate.make_record(
            "Project Zenith. Decide under earlier rules.", "current-zenith")
        with self.assertRaisesRegex(ValueError, "CURRENT_PROJECT_MISMATCH"):
            candidate.build(current, history, f["id"])

    def test_cap_below_three_and_above_24_refused(self):
        f = corpus.fixtures()[0]
        current, history = self.records(f)
        for cap in (0, 1, 2, 25, True):
            with self.assertRaisesRegex(ValueError, "INVALID_OR_INSUFFICIENT_CAP"):
                candidate.build(current, history, f["id"], cap=cap)

    def test_missing_source_or_bad_source_type_refused(self):
        f = corpus.fixtures()[0]
        current, history = self.records(f)
        with self.assertRaisesRegex(ValueError, "INVALID_HISTORY"):
            candidate.build(current, [], f["id"])
        history[0]["text"] = None
        with self.assertRaisesRegex(ValueError, "INVALID_SOURCE_RECORD"):
            candidate.build(current, history, f["id"])

    def test_partial_later_revision_refused(self):
        history = [
            candidate.make_record(
                "Project Atlas. Budget 130 euros. Deadline 6 days. "
                "Local-only requirement: true.", "old"),
            candidate.make_record(
                "Project Atlas revision: Budget 50 euros, remaining rules pending.",
                "new"),
        ]
        current = candidate.make_record(
            "Project Atlas. Decide under earlier rules.", "current")
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_LATER_RULE_SOURCE"):
            candidate.build(current, history, "Atlas")

    def test_no_model_no_semantic_authority(self):
        f = corpus.fixtures()[0]
        current, history = self.records(f)
        result = candidate.build(current, history, f["id"])
        self.assertEqual(result["native_calls"], 0)
        self.assertFalse(result["semantic_authority"])
        self.assertFalse(result["canonical_gate_pass"])


if __name__ == "__main__":
    unittest.main()
