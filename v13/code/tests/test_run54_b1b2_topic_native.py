"""Run54 native topic partition verifier negative software controls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run54_b1b2_topic_native as run54
from scripts import run54_b1b2_topic_native_verify as verify
from scripts.run52_b1b2_cross_turn_native import load_fixture
from tests.test_run52_b1b2_cross_turn import FakeRuntime

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run52_b1b2_cross_turn_seed479.json"


class Run54VerifierTests(unittest.TestCase):
    def test_forged_native_report_never_passes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"fake.json"
            p.write_text(json.dumps({
                "schema":"v13.run54.b1b2_topic_native_report.v1",
                "seed":479,"fixture_sha256":run54.FIXTURE_SHA256,
                "claim":"ORIGINAL_RUN52_HARBOR_WILLOW_STRUCTURAL_REGRESSION_NOT_UTILITY",
                "status":"TOPIC_PARTITION_NATIVE_STRUCTURAL_ONLY",
                "rows":[{"status":"RECORDED","native_model":True,"offers":[]}],
                "installed_binding_unchanged":True
            }))
            result=verify.verify(p,FIXTURE)
            self.assertEqual(result["status"],"STRUCTURAL_RED")
            self.assertIn("b1_sha",result["errors"])
            self.assertIn("offer_count",result["errors"])

    def test_original_seed479_fixture_tamper_is_rejected(self):
        data=load_fixture(FIXTURE)
        self.assertEqual([x["id"] for x in data["fixtures"]],
                         ["Harbor","Willow","Cobalt"])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"tampered.json"
            p.write_bytes(FIXTURE.read_bytes()+b" ")
            with self.assertRaisesRegex(ValueError,"RUN52_FIXTURE_SHA"):
                load_fixture(p)

    def test_fake_body_runner_cannot_claim_native(self):
        data=load_fixture(FIXTURE)
        fixtures={x["id"]:x for x in data["fixtures"]}
        with tempfile.TemporaryDirectory() as d, \
                patch.object(run54,"Runtime",FakeRuntime), \
                patch.object(run54,"installed_links",lambda *a:None):
            row=run54.run_row(Path(d)/"home",Path(d)/"installed",fixtures)
            self.assertNotEqual(row["status"],"RECORDED")
            self.assertFalse(row["native_model"])
            self.assertEqual(row["native_process_count"],0)
            self.assertTrue(row["closed_store_audit"]["ok"])


if __name__ == "__main__":
    unittest.main()
