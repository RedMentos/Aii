"""Run16 RED-first software preflight for future Keldara native pilot."""
import hashlib
import unittest
from unittest.mock import patch

from scripts import run15_step2_disjoint_bilingual_fixtures as fresh
from scripts import step2_z2_timescale as z2
from scripts import step2_z2b_seeds as z2b
from scripts import run16_step2_fresh_en_native_pilot as pilot


class FreshENPilotPreflight(unittest.TestCase):
    def test_source_fixture_and_arm_seed_pinned(self):
        reg = pilot.prereg()
        self.assertEqual(reg["fixture_sha256"], fresh.FIXTURE_SHA256)
        self.assertEqual(reg["fixture_id"], "Keldara")
        self.assertEqual(reg["fixture_limit"], 1)
        self.assertEqual(reg["seed"], 20261114)
        self.assertEqual(reg["arm"], "CQ")
        self.assertEqual(reg["variant_count"], 7)
        self.assertFalse(reg["canonical_gate_pass"])
        self.assertFalse(reg["phone_measured"])

    def test_private_harness_patch_restores_original(self):
        original = z2.FIXTURES
        with pilot.private_harness() as harness:
            self.assertEqual(harness.FIXTURES[0]["id"], "Keldara")
            self.assertEqual(len(harness.FIXTURES), 6)
            self.assertIsNot(harness.FIXTURES, original)
        self.assertIs(z2.FIXTURES, original)
        self.assertEqual(z2.FIXTURES[0]["id"], "Kestrel")

    def test_patch_restores_even_on_exception(self):
        original = z2.FIXTURES
        with self.assertRaisesRegex(RuntimeError, "SYNTHETIC"):
            with pilot.private_harness():
                raise RuntimeError("SYNTHETIC")
        self.assertIs(z2.FIXTURES, original)

    def test_settings_preserve_new_seed_and_distinct_body(self):
        settings = z2b.settings("CQ", 20261114)
        self.assertEqual(settings["seed"], 20261114)
        self.assertEqual(settings["b2_control"], "two_body")
        self.assertEqual(settings["b1_recent_source_chars"], 600)

    def test_structural_validator_never_promotes_gate(self):
        models = {"B1_DETAIL": "a" * 64, "B2_GIST": "b" * 64, "C3_LANGUAGE": "c" * 64}
        rows = [{"fixture": "Keldara", "variant": variant,
                 "status": "RECORDED", "processes_reaped": True,
                 "oracle_visible_to_native": False,
                 "native_consumer_metrics": {"status": "FINAL"}}
                for variant in pilot.VARIANTS]
        report = {"rows": rows, "fixture_sha256": fresh.FIXTURE_SHA256,
                  "preparations": [{"fixture": "Keldara", "status": "RECORDED",
                                    "model_sha256": models}],
                  "source_unchanged": True, "installed_artifacts_unchanged": True,
                  "all_structural_checks_passed": True, "distinct_bodies": True,
                  "canonical_gate_pass": False, "phone_measured": False,
                  "status": "DIAGNOSTIC_INCOMPLETE"}
        result = pilot.verify_report(report, models, {"offers": 12, "with_question": 12})
        self.assertFalse(result["canonical_gate_pass"])
        report["phone_measured"] = True
        with self.assertRaises(ValueError):
            pilot.verify_report(report, models, {"offers": 12, "with_question": 12})

    def test_no_native_execution_from_import_or_prereg(self):
        with patch("v13.runners.LlamaRunner.generate", side_effect=AssertionError("NATIVE_CALLED")):
            reg = pilot.prereg()
        self.assertEqual(reg["scope"], "LINUX_NATIVE_FUTURE_ONE_FIXTURE_ONLY")


if __name__ == "__main__":
    unittest.main()
