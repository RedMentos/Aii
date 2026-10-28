"""Run33 independent adversarial structural checks for Run33 native preflight.

No models are installed or executed; a fabricated report is never native proof.
"""
import copy
import unittest
from unittest.mock import patch

from scripts import run15_step2_disjoint_bilingual_fixtures as fresh
from scripts import run33_step2_lysoria_en_rule_native_pilot as pilot


class NativePilotAdversarialReview(unittest.TestCase):
    def setUp(self):
        self.models = {"B1_DETAIL": "a" * 64,
                       "B2_GIST": "b" * 64,
                       "C3_LANGUAGE": "c" * 64}
        self.counts = {"offers": 12, "with_question": 12}
        self.report = {
            "rows": [
                {"fixture": "Lysoria", "variant": v, "status": "RECORDED",
                 "processes_reaped": True, "oracle_visible_to_native": False,
                 "native_consumer_metrics": {"status": "FINAL"}}
                for v in pilot.VARIANTS
            ],
            "preparations": [
                {"fixture": "Lysoria", "status": "RECORDED",
                 "model_sha256": dict(self.models)}
            ],
            "fixture_sha256": fresh.FIXTURE_SHA256,
            "source_unchanged": True, "installed_artifacts_unchanged": True,
            "all_structural_checks_passed": True, "distinct_bodies": True,
            "canonical_gate_pass": False, "phone_measured": False,
            "status": "DIAGNOSTIC_INCOMPLETE",
        }

    def test_clean_structure_remains_scoped_only(self):
        result = pilot.verify_report(self.report, self.models, self.counts)
        self.assertEqual(result["rows"], 7)
        self.assertFalse(result["canonical_gate_pass"])
        self.assertFalse(result["whole_system_complete"])
        self.assertEqual(result["age_authority"], 0)

    def test_fail_closed_on_invalid_rows_or_proof_claims(self):
        attacks = {
            "duplicate_variant": lambda x: x["rows"][0].update(
                variant=x["rows"][1]["variant"]),
            "wrong_fixture": lambda x: x["rows"][0].update(fixture="Aquila"),
            "native_not_final": lambda x: x["rows"][0]["native_consumer_metrics"].update(
                status="ERROR"),
            "not_reaped": lambda x: x["rows"][0].update(processes_reaped=False),
            "oracle_leak": lambda x: x["rows"][0].update(oracle_visible_to_native=True),
            "wrong_fixture_hash": lambda x: x.update(fixture_sha256="0" * 64),
            "wrong_prep_model": lambda x: x["preparations"][0]["model_sha256"].update(
                B2_GIST="0" * 64),
            "wrong_prep_status": lambda x: x["preparations"][0].update(status="ERROR"),
            "source_changed": lambda x: x.update(source_unchanged=False),
            "installed_changed": lambda x: x.update(installed_artifacts_unchanged=False),
            "missing_structural": lambda x: x.update(all_structural_checks_passed=False),
            "same_body": lambda x: x.update(distinct_bodies=False),
            "phone_promoted": lambda x: x.update(phone_measured=True),
            "gate_promoted": lambda x: x.update(canonical_gate_pass=True),
            "report_status_promoted": lambda x: x.update(status="UTILITY_PASS_SCOPED"),
        }
        for label, change in attacks.items():
            with self.subTest(label=label):
                candidate = copy.deepcopy(self.report)
                change(candidate)
                with self.assertRaises(ValueError):
                    pilot.verify_report(candidate, self.models, self.counts)

    def test_question_counts_and_model_identity_cannot_be_spoofed(self):
        for counts in ({"offers": 12, "with_question": 11},
                       {"offers": True, "with_question": 12},
                       {"offers": 13, "with_question": 12}):
            with self.subTest(counts=counts):
                with self.assertRaises(ValueError):
                    pilot.verify_report(self.report, self.models, counts)
        for replacement in ("b" * 64, "not_sha256", None):
            with self.subTest(replacement=replacement):
                models = dict(self.models, B1_DETAIL=replacement)
                with self.assertRaises(ValueError):
                    pilot.verify_report(self.report, models, self.counts)

    def test_frozen_source_and_runner_pins_refuse_drift(self):
        with patch.object(pilot, "RUN15_SOURCE_BLOB", "0" * 40):
            with self.assertRaises(ValueError):
                pilot.prereg()
        with patch.object(pilot, "PINNED_RUNNER_TAR_SHA256", "0" * 64):
            with self.assertRaises(ValueError):
                pilot.prereg()
        changed = dict(pilot.PINNED_SOURCE_BLOBS)
        changed["scripts/step2_z2b_seeds.py"] = "0" * 40
        with patch.object(pilot, "PINNED_SOURCE_BLOBS", changed):
            with self.assertRaises(ValueError):
                pilot.prereg()

    def test_prereg_only_does_not_modify_frozen_alias(self):
        original = pilot.z2.FIXTURES
        before = pilot.prereg()
        after = pilot.prereg()
        self.assertEqual(before, after)
        self.assertIs(pilot.z2.FIXTURES, original)
        self.assertEqual(before["arm"], "CQ")
        self.assertEqual(before["seed"], 20261115)


if __name__ == "__main__":
    unittest.main()
