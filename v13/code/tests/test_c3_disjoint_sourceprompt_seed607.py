"""Seed607 disjoint C3 source-prompt software guards; no native model claims."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import c3_disjoint_sourceprompt_seed607_native as probe
from scripts import c3_disjoint_sourceprompt_seed607_verify as verify
from tests.test_run52_b1b2_cross_turn import FakeRuntime

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/c3_sourceprompt_seed607.json")


class C3Seed607Tests(unittest.TestCase):
    def test_registered_fixture_order_and_tamper(self):
        fixture = probe.load_fixture(FIXTURE)
        self.assertEqual([x["id"] for x in fixture["cases"]],
                         ["Ambercrest", "Foxglove", "Northstarlet"])
        self.assertEqual([x["order"][0] for x in fixture["cases"]],
                         list(probe.ARMS))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "tampered.json"
            p.write_bytes(FIXTURE.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "C3_SEED607_FIXTURE_SHA"):
                probe.load_fixture(p)

    def test_prompt_arms_preserve_exact_source_and_no_answer_template(self):
        fixture = probe.load_fixture(FIXTURE)
        for case in fixture["cases"]:
            for arm in probe.ARMS:
                with self.subTest(case=case["id"], arm=arm):
                    msgs = probe.prompts(arm, case["source"])
                    self.assertEqual([x["role"] for x in msgs], ["system", "user"])
                    self.assertIn(case["source"], msgs[1]["content"])
                    self.assertNotIn("73 Euro.", msgs[0]["content"])
                    self.assertNotIn("28 Euro.", msgs[0]["content"])
                    self.assertNotIn("91 Euro.", msgs[0]["content"])
                    if arm == "JSON_ENVELOPE":
                        payload = json.loads(msgs[1]["content"])
                        self.assertFalse(payload["body_hypotheses_are_facts"])
                        self.assertEqual(payload["body_observations"], [])

    def test_frozen_scorer_positive_and_negative_controls(self):
        good = "Project Ambercrest budget is 73 Euro."
        self.assertEqual(probe.score(good, "Ambercrest", 73),
                         {"numeric": 1, "strict": 1})
        self.assertEqual(verify.score_again(good, "Ambercrest", 73),
                         {"numeric": 1, "strict": 1})
        for bad in (
            "Project Ambercrest budget is 74 Euro.",
            "Project Ambercrest budget is not 73 Euro.",
            "Project Ambercrest budget is 73 Euro and 19 Euro.",
            "Project Foxglove budget is 73 Euro.",
            "No amount is known for Project Ambercrest.",
        ):
            with self.subTest(bad=bad):
                self.assertEqual(probe.score(bad, "Ambercrest", 73)["numeric"], 0)
                self.assertEqual(verify.score_again(bad, "Ambercrest", 73)["numeric"], 0)
        self.assertEqual(probe.score("The budget is 73.", "Ambercrest", 73),
                         {"numeric": 1, "strict": 0})

    def test_fake_body_cannot_claim_native_c3(self):
        with tempfile.TemporaryDirectory() as d, \
                patch.object(probe, "Runtime", FakeRuntime), \
                patch.object(probe, "installed_links", lambda *a: None), \
                patch.object(probe, "installed_artifacts",
                             lambda *a: {"model_sha256": {}, "runner_sha256": "fake"}):
            report = probe.run(Path(d), Path(d) / "output", FIXTURE)
            self.assertEqual(report["status"], "STRUCTURAL_RED")
            self.assertEqual(len(report["rows"]), 9)
            self.assertFalse(report["processes_reaped"])
            self.assertEqual(report["native_process_count"], 0)
            self.assertTrue(report["no_live_output"])
            self.assertEqual(report["tool_dispatches"], 0)
            self.assertEqual(report["learning_authority"], 0)
            self.assertTrue(report["closed_store_audit"]["ok"])

    def test_forged_report_is_structural_red(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "forged.json"
            p.write_text(json.dumps({
                "schema": "v13.c3_disjoint_sourceprompt_native.v1",
                "seed": 607, "max_tokens": 64,
                "fixture_sha256": probe.FIXTURE_SHA256,
                "status": "UTILITY_GREEN_DIAGNOSTIC",
                "rows": [], "native_process_count": 9,
                "processes_reaped": True, "no_live_output": True,
            }))
            result = verify.verify(p, FIXTURE)
            self.assertEqual(result["status"], "STRUCTURAL_RED")
            self.assertIn("row_count", result["errors"])


if __name__ == "__main__":
    unittest.main()
