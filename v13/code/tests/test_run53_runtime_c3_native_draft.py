"""Run53 native evidence verifier negative controls; no native model in unit tests."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run53_runtime_c3_native_draft as run53
from scripts import run53_runtime_c3_native_draft_verify as verify
from scripts.run51_f1f5_second_attempt_native import load_fixture
from tests.test_run52_b1b2_cross_turn import FakeRuntime

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run51_f1f5_second_attempt_seed467.json"


class Run53NativeDraftVerifierTests(unittest.TestCase):
    def test_reject_forged_report_without_real_native_receipts(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"report.json"
            p.write_text(json.dumps({
                "schema": "v13.run53.runtime_c3_native_draft_report.v1",
                "seed": 467, "fixture_sha256": run53.FIXTURE_SHA256,
                "claim": "ORIGINAL_RUN51_CYPRESS_STRUCTURAL_REGRESSION_NOT_UTILITY",
                "status": "NATIVE_DRAFT_STRUCTURAL_ONLY",
                "installed_binding_unchanged": True,
                "rows": [{"fixture":"Cypress","status":"RECORDED",
                          "native_model":True,"model_calls":1}],
                "row_sha256": {}
            }))
            r = verify.verify(p, FIXTURE)
            self.assertEqual(r["status"], "STRUCTURAL_RED")
            self.assertIn("c3_model_sha", r["errors"])
            self.assertIn("row_hash", r["errors"])
            self.assertIn("native_final", r["errors"])

    def test_original_run51_fixture_hash_and_cohort_are_immutable(self):
        f = load_fixture(FIXTURE)["fixtures"]
        self.assertEqual([x["id"] for x in f], ["Cypress","Lark","Delta"])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"bad.json"
            p.write_bytes(FIXTURE.read_bytes()+b" ")
            with self.assertRaisesRegex(ValueError, "RUN51_FIXTURE_SHA"):
                load_fixture(p)

    def test_synthetic_runner_cannot_claim_native_in_real_store(self):
        f = load_fixture(FIXTURE)["fixtures"][0]
        with tempfile.TemporaryDirectory() as d, \
                patch.object(run53, "Runtime", FakeRuntime), \
                patch.object(run53, "installed_links", lambda *a: None):
            row = run53.run_row(Path(d)/"home", Path(d)/"installed", f)
            self.assertNotEqual(row["status"], "RECORDED")
            self.assertFalse(row["native_model"])
            self.assertEqual(row["model_calls"], 0)
            self.assertEqual(row["off_control"]["status"], "OFF")
            self.assertEqual(row["missing_correction_control"]["status"], "CLARIFY")
            self.assertEqual(row["draft_result"]["status"], "GENERATION_ERROR")
            self.assertTrue(row["closed_store_audit"]["ok"])


if __name__ == "__main__":
    unittest.main()
