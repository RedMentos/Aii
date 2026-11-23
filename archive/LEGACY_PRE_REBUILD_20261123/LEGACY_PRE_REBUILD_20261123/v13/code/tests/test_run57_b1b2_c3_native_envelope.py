"""Run57 five-call native source-envelope preflight negative software controls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run57_b1b2_c3_native_envelope as run57
from scripts import run57_b1b2_c3_native_verify as verify57
from scripts.run52_b1b2_cross_turn_native import load_fixture
from tests.test_run52_b1b2_cross_turn import FakeRuntime

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run52_b1b2_cross_turn_seed479.json"


class Run57NativeEnvelopeTests(unittest.TestCase):
    def test_forged_native_report_cannot_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"forged.json"
            p.write_text(json.dumps({
                "schema": "v13.run57.b1b2_c3_native_report.v1",
                "seed": 479, "fixture_sha256": run57.FIXTURE_SHA256,
                "claim": "ORIGINAL_RUN52_HARBOR_B1B2_C3_STRUCTURAL_REPLAY_NOT_UTILITY",
                "status": "B1B2_C3_NATIVE_ENVELOPE_STRUCTURAL_ONLY",
                "installed_binding_unchanged": True,
                "rows": [{"status":"RECORDED","native_model":True,"body_offers":[]}],
            }))
            result = verify57.verify(p, FIXTURE)
            self.assertEqual(result["status"], "STRUCTURAL_RED")
            self.assertIn("model_sha_B1_DETAIL", result["errors"])
            self.assertIn("body_offer_count", result["errors"])

    def test_original_seed479_fixture_is_frozen(self):
        data = load_fixture(FIXTURE)
        self.assertEqual([x["id"] for x in data["fixtures"]],
                         ["Harbor","Willow","Cobalt"])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"bad.json"
            p.write_bytes(FIXTURE.read_bytes()+b" ")
            with self.assertRaisesRegex(ValueError, "RUN52_FIXTURE_SHA"):
                load_fixture(p)

    def test_fake_body_runner_never_claims_native_or_output(self):
        data = load_fixture(FIXTURE)
        fixture = next(x for x in data["fixtures"] if x["id"] == "Harbor")
        with tempfile.TemporaryDirectory() as d, \
                patch.object(run57, "Runtime", FakeRuntime), \
                patch.object(run57, "installed_links", lambda *a: None):
            row = run57.run_row(Path(d)/"home", Path(d)/"installed", fixture)
            self.assertNotEqual(row["status"], "RECORDED")
            self.assertFalse(row["native_model"])
            self.assertEqual(row["native_process_count"], 0)
            self.assertTrue(row["closed_store_audit"]["ok"])
            self.assertIsNone(row["c3"])

    def test_distinct_pinned_models_and_runner_are_not_forged(self):
        self.assertNotEqual(verify57.PINS["B1_DETAIL"][0],
                            verify57.PINS["B2_GIST"][0])
        self.assertNotEqual(verify57.PINS["B2_GIST"][0],
                            verify57.PINS["C3_LANGUAGE"][0])
        self.assertEqual(verify57.PINS["C3_LANGUAGE"][1],
                         "LFM2.5-350M-QAD-Q4_0.gguf")


if __name__ == "__main__":
    unittest.main()
