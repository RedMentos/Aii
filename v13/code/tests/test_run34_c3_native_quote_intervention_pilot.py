"""Run34 C3-only native pilot preflight/refusal tests; no native execution."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import run33_b2_c3_counterfactual_envelopes as cf
from scripts import run34_c3_native_quote_intervention_pilot as pilot


class Run34NativePilotPreflight(unittest.TestCase):
    def test_current_source_drift_refused_and_frozen_metadata_preserved(self):
        # Historical Run34 prereg remains bound to its ORIGINAL utility bytes.
        # A later score-validation hardening changed the live utility module.
        utility_path = pilot.ROOT / "v13/utility.py"
        live_blob = pilot._git_blob(utility_path)
        self.assertEqual(live_blob, "ff16ab6012b2865e0f3abde2a289aaf00e9aaa53")
        self.assertNotEqual(live_blob, pilot.FROZEN_UTILITY_BLOB)
        with self.assertRaisesRegex(ValueError, "native_source_or_catalog_changed"):
            pilot.prereg()

        # Test ONLY the frozen prereg metadata contract with the historical
        # utility hash simulated; no source, runner or model is repinned.
        real_blob = pilot._git_blob

        def historical_utility_only(path):
            if path == utility_path:
                return pilot.FROZEN_UTILITY_BLOB
            return real_blob(path)

        with mock.patch.object(pilot, "_git_blob", side_effect=historical_utility_only):
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

    def test_forged_metrics_score_and_raw_hash_cannot_pass_native_proof(self):
        from v13.common import dumps
        import hashlib
        rows = []
        row_hashes = {}
        for arm in pilot.ARMS:
            envelope = cf.build_envelope(pilot.FIXTURE, arm, pilot.SEED)
            row = {
                "arm": arm, "envelope": envelope, "raw_answer": "{}",
                "raw_answer_sha256": "0" * 64,
                "score": {"utility": 1.0, "forged": True},
                "native_status": "FINAL",
                "native_metrics": {"status": "ERROR", "actual_model": "forged"},
                "process_reaped": True, "oracle_visible_to_native": False,
                "model_sha256": pilot.C3_GGUF_SHA256,
                "runner_sha256": "a" * 64, "envelope_verified": True,
            }
            rows.append(row)
            row_hashes[arm] = hashlib.sha256(dumps(row).encode()).hexdigest()
        report = {
            "schema": "v13.run34.c3_only.native_pilot.raw.v1",
            "fixture_id": pilot.FIXTURE, "seed": pilot.SEED,
            "model_sha256": pilot.C3_GGUF_SHA256,
            "runner_sha256": "a" * 64,
            "rows": rows, "row_sha256": row_hashes,
            "canonical_gate_pass": False, "phone_measured": False,
            "jepa_weight": 0,
        }
        # The rows are synthetic adversarial forgeries, NEVER native evidence.
        with self.assertRaises(ValueError):
            pilot.verify_report(report, pilot.C3_GGUF_SHA256, "a" * 64)

    def test_native_source_pins_cover_run33_runner_and_scorer(self):
        self.assertEqual(pilot.RUN33_SOURCE_BLOB,
                         "b1d58d7e0c3937787cf15dd801e278de25845879")
        self.assertEqual(pilot.FROZEN_RUNNERS_BLOB,
                         "efda7aa1aa5729e974d0d641870d4da05d21c961")
        self.assertEqual(pilot.FROZEN_UTILITY_BLOB,
                         "f4a92dab9c4a40761d64394cdca1c052e9a76bfd")


if __name__ == "__main__":
    unittest.main()
