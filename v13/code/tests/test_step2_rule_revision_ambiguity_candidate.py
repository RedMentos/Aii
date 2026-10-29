"""STEP2 source revision ambiguity regressions (software-only)."""
from __future__ import annotations
import hashlib
import unittest
from scripts import run109_step2_fresh_fixtures as corpus
from scripts import run118_step2_rule_pointer_choice_candidate as pointer
from scripts import step2_rule_revision_ambiguity_candidate as guarded


class Step2RuleRevisionAmbiguity(unittest.TestCase):
    def records(self, fixture):
        history = [pointer.make_record(s, fixture["id"] + "-h" + str(i))
                   for i, s in enumerate(fixture["history"])]
        return (pointer.make_record(fixture["current"], fixture["id"] + "-current"),
                history)

    def test_frozen_six_exact_choices_and_negative_gates(self):
        report = guarded.evaluate()
        self.assertEqual(report["candidate_covered"], 6)
        self.assertEqual(report["fixture_sha256"], pointer.FIXTURE_SHA256)
        self.assertEqual(report["native_calls"], 0)
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_status"], "UTILITY_FAIL")
        for fixture in corpus.fixtures():
            current, history = self.records(fixture)
            original = pointer.build(current, history, fixture["id"])
            result = guarded.build(current, history, fixture["id"])
            self.assertEqual(result["choices"], original["choices"])
            self.assertEqual(result["selected_prior_span_sha256"],
                             original["selected_prior_span_sha256"])
            self.assertFalse(result["semantic_authority"])
            self.assertLessEqual(len(result["choices"]), 24)
            by_id = {r["source_ref"]["source_id"]: r["text"]
                     for r in history + [current]}
            for choice in result["choices"]:
                ref = choice["source_ref"]
                source = by_id[ref["source_id"]]
                self.assertEqual(choice["text"], source[ref["char_start"]:ref["char_end"]])
                self.assertEqual(ref["sha256"], hashlib.sha256(source.encode()).hexdigest())

    def test_current_complete_rule_change_refused_not_stale(self):
        fixture = corpus.fixtures()[0]
        _, history = self.records(fixture)
        current = pointer.make_record(
            "Project Atlas. Budget 50 euros. Deadline 2 days. "
            "Local-only requirement: false. Decide under new rules.", "now")
        self.assertTrue(pointer.build(current, history, "Atlas")["candidate_covered"])
        with self.assertRaisesRegex(ValueError, "CURRENT_MESSAGE_RULE_UPDATE_UNRESOLVED"):
            guarded.build(current, history, "Atlas")

    def test_current_partial_rule_change_refused(self):
        _, history = self.records(corpus.fixtures()[0])
        current = pointer.make_record(
            "Project Atlas. Budget 50 euros, remaining fields pending.", "now")
        with self.assertRaisesRegex(ValueError, "CURRENT_MESSAGE_RULE_UPDATE_UNRESOLVED"):
            guarded.build(current, history, "Atlas")

    def test_current_explicit_change_without_values_refused(self):
        _, history = self.records(corpus.fixtures()[0])
        current = pointer.make_record("Project Atlas. Updated project rules apply.", "now")
        with self.assertRaisesRegex(ValueError, "CURRENT_MESSAGE_RULE_UPDATE_UNRESOLVED"):
            guarded.build(current, history, "Atlas")

    def test_later_nonprefix_complete_revision_refused(self):
        current, history = self.records(corpus.fixtures()[0])
        history.append(pointer.make_record(
            "Meeting note: Project Atlas. Budget 50 euros. Deadline 2 days. "
            "Local-only requirement: false.", "later"))
        self.assertTrue(pointer.build(current, history, "Atlas")["candidate_covered"])
        with self.assertRaisesRegex(ValueError, "UNRESOLVED_LATER_PROJECT_RULE_SOURCE"):
            guarded.build(current, history, "Atlas")

    def test_later_lowercase_partial_revision_refused(self):
        current, history = self.records(corpus.fixtures()[0])
        history.append(pointer.make_record(
            "project Atlas revision: budget changed; details pending.", "later"))
        with self.assertRaisesRegex(ValueError, "UNRESOLVED_LATER_PROJECT_RULE_SOURCE"):
            guarded.build(current, history, "Atlas")

    def test_later_explicit_change_without_values_refused(self):
        current, history = self.records(corpus.fixtures()[0])
        history.append(pointer.make_record(
            "Meeting for Project Atlas: rules were updated yesterday.", "later"))
        with self.assertRaisesRegex(ValueError, "UNRESOLVED_LATER_PROJECT_RULE_SOURCE"):
            guarded.build(current, history, "Atlas")

    def test_unrelated_rules_and_explicit_no_change_allowed(self):
        current, history = self.records(corpus.fixtures()[0])
        history.append(pointer.make_record(
            "Project Zenith. Budget 50 euros. Deadline 2 days. "
            "Local-only requirement: false.", "zenith"))
        history.append(pointer.make_record(
            "Project Atlas status note. No project rule changed.", "neutral"))
        self.assertTrue(guarded.build(current, history, "Atlas")["candidate_covered"])

    def test_supplier_revision_not_rule_revision(self):
        current, history = self.records(corpus.fixtures()[0])
        history.append(pointer.make_record(
            "Project Atlas supplier data sheet revision 3. Two offers confirmed.", "sheet"))
        self.assertTrue(guarded.build(current, history, "Atlas")["candidate_covered"])

    def test_tampered_ref_and_duplicate_id_refused(self):
        current, history = self.records(corpus.fixtures()[0])
        history[0]["source_ref"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_REF_BINDING_RED"):
            guarded.build(current, history, "Atlas")
        current, history = self.records(corpus.fixtures()[0])
        current["source_ref"]["source_id"] = history[0]["source_ref"]["source_id"]
        with self.assertRaisesRegex(ValueError, "DUPLICATE_SOURCE_ID"):
            guarded.build(current, history, "Atlas")

    def test_bad_project_and_cap_refused(self):
        current, history = self.records(corpus.fixtures()[0])
        for project in ("", "Atlas/Zenith", None):
            with self.assertRaisesRegex(ValueError, "INVALID_PROJECT"):
                guarded.build(current, history, project)
        for cap in (0, 2, 25, True):
            with self.assertRaisesRegex(ValueError, "INVALID_OR_INSUFFICIENT_CAP"):
                guarded.build(current, history, "Atlas", cap=cap)


if __name__ == "__main__":
    unittest.main()
