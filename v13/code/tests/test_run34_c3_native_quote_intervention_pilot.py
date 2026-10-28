"""Run34 C3-only native pilot preflight/refusal tests; no native execution."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import run33_b2_c3_counterfactual_envelopes as cf
from scripts import run34_c3_native_quote_intervention_pilot as pilot


class Run34NativePilotPreflight(unittest.TestCase):
    def test_pinned_source_model_runner_and_negative_gates(self):
        reg = pilot.prereg()
        self.assertEqual(reg["fixture_id"], "Velaris")
        self.assertEqual(reg["seed"], 20261121)
        self.assertEqual(reg["arms"], list(cf.ARMS))
        self.assertEqual(reg["c3_model_sha256"], pilot.C3_GGUF_SHA256)
        self.assertEqual(reg["runner_tar_sha256"], pilot.RUNNER_TAR_SHA256)
        self.assertIs(reg["native_executed"], False)
        self.assertIs(reg["canonical_gate_pass"], False)
        self.assertIs(reg["phone_measured"], False)
        self.assertEqual(reg["jepa_weight"], 0)

    def test_no_installed_home_no_native_no_evidence_created(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            home = base / "missing-installed-home"
            evidence = base / "fresh-evidence"
            with mock.patch.object(pilot.LlamaRunner, "__init__",
                                   side_effect=AssertionError("native unexpectedly opened")):
                with self.assertRaises(ValueError):
                    pilot.run(home, evidence)
            self.assertFalse(evidence.exists())
            self.assertFalse(home.exists())

    def test_existing_evidence_dir_refused_without_native(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            home = base / "missing-installed-home"
            evidence = base / "existing"
            evidence.mkdir()
            with mock.patch.object(pilot.LlamaRunner, "__init__",
                                   side_effect=AssertionError("native unexpectedly opened")):
                with self.assertRaises(ValueError):
                    pilot.run(home, evidence)
            self.assertEqual(list(evidence.iterdir()), [])

    def test_report_cannot_pass_without_real_native_rows(self):
        report = {
            "schema": "v13.run34.c3_only.native_pilot.raw.v1",
            "fixture_id": "Velaris", "seed": 20261121,
            "model_sha256": pilot.C3_GGUF_SHA256,
            "runner_sha256": "a" * 64,
            "rows": [], "row_sha256": {},
            "canonical_gate_pass": False, "phone_measured": False,
            "jepa_weight": 0,
        }
        with self.assertRaises(ValueError):
            pilot.verify_report(report, pilot.C3_GGUF_SHA256, "a" * 64)
        report["rows"] = [{"arm": arm, "native_status": "FINAL",
                           "process_reaped": True, "oracle_visible_to_native": False,
                           "raw_answer": "{}"} for arm in pilot.ARMS]
        report["row_sha256"] = {arm: "0" * 64 for arm in pilot.ARMS}
        with self.assertRaises(ValueError):
            pilot.verify_report(report, pilot.C3_GGUF_SHA256, "a" * 64)

    def test_source_envelopes_oracle_free_and_only_source_exact(self):
        for arm in pilot.ARMS:
            envelope = cf.build_envelope(pilot.FIXTURE, arm, pilot.SEED)
            self.assertTrue(cf.verify_envelope(envelope))
            context = json.loads(envelope["messages"][1]["content"])
            self.assertEqual(set(context), {"current_source", "analysts"})
            self.assertNotIn("oracle", context)
            self.assertFalse(envelope["native_executed"])


if __name__ == "__main__":
    unittest.main()
