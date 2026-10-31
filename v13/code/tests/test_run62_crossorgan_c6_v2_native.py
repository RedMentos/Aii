"""Run62 five-call cross-organ C6 native preflight negative software tests."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run62_crossorgan_c6_v2_native as run62
from scripts import run62_crossorgan_c6_v2_verify as verify62
from scripts.run51_f1f5_second_attempt_native import load_fixture
from tests.test_run52_b1b2_cross_turn import FakeRuntime

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run51_f1f5_second_attempt_seed467.json"


class Run62CrossOrganNativeTests(unittest.TestCase):
    def test_forged_native_and_tty_report_never_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"forged.json"
            p.write_text(json.dumps({
                "schema":"v13.run62.crossorgan_c6_v2_native_report.v1",
                "seed":467, "fixture_sha256":run62.FIXTURE_SHA256,
                "claim":"ORIGINAL_RUN51_CYPRESS_RUN62_C6_V2_ENGINEERING_SHADOW_NOT_UTILITY",
                "status":"C6_V2_PREFLIGHT_ONLY_NO_APPROVAL",
                "installed_binding_unchanged":True,
                "rows":[{"status":"RECORDED_C6_V2_PREFLIGHT_ONLY",
                         "native_model":True,"tty_approved":True,
                         "body_offers":[]}]}))
            result = verify62.verify(p,FIXTURE)
            self.assertEqual(result["status"],"STRUCTURAL_RED")
            self.assertIn("model_sha_B1_DETAIL",result["errors"])
            self.assertIn("body_offer_count",result["errors"])

    def test_original_seed467_fixture_unchanged(self):
        data = load_fixture(FIXTURE)
        self.assertEqual([x["id"] for x in data["fixtures"]],
                         ["Cypress","Lark","Delta"])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"tampered.json"
            p.write_bytes(FIXTURE.read_bytes()+b" ")
            with self.assertRaisesRegex(ValueError,"RUN51_FIXTURE_SHA"):
                load_fixture(p)

    def test_fake_body_never_claims_native_c6(self):
        f=load_fixture(FIXTURE)["fixtures"][0]
        with tempfile.TemporaryDirectory() as d, \
                patch.object(run62,"Runtime",FakeRuntime), \
                patch.object(run62,"installed_links",lambda *a:None):
            row=run62.run_row(Path(d)/"home",Path(d)/"installed",f)
            self.assertNotIn(row["status"],("RECORDED_C6_V2_PREFLIGHT_ONLY",
                                             "RECORDED_C6_V2_GROUNDING_RED"))
            self.assertFalse(row["native_model"])
            self.assertEqual(row["native_process_count"],0)
            self.assertFalse(row["tty_approved"])
            self.assertFalse(row["output_committed"])
            self.assertTrue(row["closed_store_audit"]["ok"])

    def test_distinct_pinned_models(self):
        self.assertEqual(verify62.PINS["C3_LANGUAGE"][1],
                         "LFM2.5-350M-QAD-Q4_0.gguf")
        self.assertNotEqual(verify62.PINS["B1_DETAIL"][0],
                            verify62.PINS["B2_GIST"][0])
        self.assertNotEqual(verify62.PINS["B2_GIST"][0],
                            verify62.PINS["C3_LANGUAGE"][0])


if __name__ == "__main__":
    unittest.main()
