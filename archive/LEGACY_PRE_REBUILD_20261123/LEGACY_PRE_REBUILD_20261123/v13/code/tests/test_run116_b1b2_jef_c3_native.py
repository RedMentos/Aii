"""Run116 seed1019 frozen fixture and real Store synthetic-body preflight."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts import run116_b1b2_jef_c3_native as pilot

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/RUN116_B1B2_JEF_C3_SEED1019.json")


class Run116PreflightTests(unittest.TestCase):
    def test_frozen_disjoint_fixture_and_three_arms(self):
        rows = pilot.fixture(FIXTURE)
        self.assertEqual([r["id"] for r in rows], list(pilot.IDS))
        self.assertEqual([tuple(r["oracle"].values()) for r in rows],
                         list(pilot.EXPECTED))
        self.assertEqual(pilot.ARMS,
                         ("RAW_TWO_SOURCE_ROLE", "TYPED_JEF_ROLE",
                          "TYPED_JEF_WITH_BODY_ROLE"))

    def test_fixture_byte_tamper_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "tampered.json"
            p.write_bytes(FIXTURE.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "RUN116_FROZEN_FIXTURE_SHA_RED"):
                pilot.fixture(p)

    def test_real_sqlite_context_and_wrong_synthetic_bodies_no_native_proof(self):
        with tempfile.TemporaryDirectory() as d:
            work, out = Path(d) / "work", Path(d) / "out"
            report = pilot.run(FIXTURE, work, out)
            self.assertEqual(report["status"],
                             "MODEL_FREE_SIX_CASE_PREFLIGHT_PASS", report)
            self.assertFalse(report["native"])
            self.assertTrue(report["synthetic_body_observers"])
            self.assertEqual(report["native_body_calls"], 0)
            self.assertEqual(report["native_c3_calls"], 0)
            self.assertEqual(report["native_jef_calls"], 0)
            self.assertFalse(report["output_committed"])
            self.assertEqual(report["tool_dispatches"], 0)
            self.assertEqual(report["learning_authority"], 0)
            self.assertEqual(report["delivery_authority"], 0)
            self.assertEqual(report["step2_exit"], "EVIDENCE_NOT_PASSING")
            self.assertEqual(report["jepa_weight"], 0)
            self.assertEqual(len(report["rows"]), 6)
            for row in report["rows"]:
                with self.subTest(project=row["id"]):
                    self.assertEqual(row["status"], "MODEL_FREE_PREFLIGHT_PASS")
                    self.assertTrue(row["closed_store_ok"])
                    self.assertTrue(row["no_live_output"])
                    self.assertEqual(row["verified_quote_count"], 0)
                    self.assertEqual(
                        [(x["role"], x["phase"]) for x in row["offers"]],
                        [("B2_GIST", "prior"), ("B1_DETAIL", "current"),
                         ("B2_GIST", "current")])
                    self.assertEqual(len(row["arms"]), 3)
                    for arm in row["arms"]:
                        self.assertEqual(arm["status"], "MODEL_FREE_PROMPT_VERIFIED")
                        self.assertFalse(arm["native_final"])
                        self.assertEqual([m["role"] for m in arm["messages"]],
                                         ["system", "user"])
                        self.assertNotIn("oracle", arm["messages"][0]["content"].lower())
                        self.assertNotIn(row["id"], arm["messages"][0]["content"])
                        payload = json.loads(arm["messages"][1]["content"])
                        self.assertEqual(
                            [s["source_ref"] for s in payload["sources"]],
                            [row["prior_source_ref"], row["current_source_ref"]])
                        if arm["arm"] == pilot.ARMS[2]:
                            self.assertFalse(payload["body_hypotheses_are_facts"])
                            self.assertEqual(
                                [x["hypothesis_authority"]
                                 for x in payload["body_observations"]],
                                ["MODEL_HYPOTHESIS_NOT_FACT"] * 2)
            self.assertEqual(json.loads((out / "report.json").read_text()), report)

    def test_fresh_work_report_paths_required(self):
        with tempfile.TemporaryDirectory() as d:
            work, out = Path(d) / "work", Path(d) / "out"
            work.mkdir()
            with self.assertRaises(FileExistsError):
                pilot.run(FIXTURE, work, out)


if __name__ == "__main__":
    unittest.main()
