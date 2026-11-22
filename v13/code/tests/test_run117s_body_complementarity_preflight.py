"""Run117S six-case model-free B1/B2 salience preflight acceptance."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts import run117s_body_complementarity_preflight as pilot

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/RUN117S_BODY_COMPLEMENTARITY_SEED1061.json")


class Run117SPreflightTests(unittest.TestCase):
    def test_frozen_disjoint_oracles_and_arms(self):
        rows = pilot.fixture(FIXTURE)
        self.assertEqual([r["id"] for r in rows], list(pilot.IDS))
        self.assertEqual(pilot.ARMS,
                         ("RAW_FULL_SOURCES", "SOURCE_SPANS_ONLY",
                          "BODY_VERIFIED_QUOTES"))
        self.assertEqual([r["oracle"] for r in rows], [
            {"choice": "A", "remaining": 50},
            {"choice": "B", "remaining": 70},
            {"choice": "NONE", "remaining": None},
            {"choice": "A", "remaining": 50},
            {"choice": "A", "remaining": 50},
            {"choice": "NONE", "remaining": None}])

    def test_frozen_fixture_byte_tamper_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "mutated.json"
            p.write_bytes(FIXTURE.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError,
                                        "FROZEN_RUN117S_FIXTURE_SHA_RED"):
                pilot.fixture(p)

    def test_six_real_store_synthetic_body_source_only_prompts(self):
        with tempfile.TemporaryDirectory() as d:
            work, out = Path(d) / "work", Path(d) / "report"
            report = pilot.run(FIXTURE, work, out)
            self.assertEqual(report["status"],
                             "MODEL_FREE_SIX_CASE_PREFLIGHT_PASS", report)
            self.assertFalse(report["native"])
            self.assertTrue(report["synthetic_body_observers"])
            self.assertEqual(report["native_c3_calls"], 0)
            self.assertEqual(report["native_jef_calls"], 0)
            self.assertEqual(report["tool_dispatches"], 0)
            self.assertFalse(report["output_committed"])
            self.assertEqual(report["learning_authority"], 0)
            self.assertEqual(report["delivery_authority"], 0)
            self.assertEqual(report["jepa_weight"], 0)
            self.assertFalse(report["whole_system_complete"])
            self.assertEqual(len(report["rows"]), 6)
            for entry, fixture in zip(report["rows"], pilot.fixture(FIXTURE)):
                with self.subTest(project=fixture["id"]):
                    self.assertEqual(entry["status"],
                                     "MODEL_FREE_PREFLIGHT_PASS")
                    self.assertTrue(entry["closed_store_ok"])
                    self.assertTrue(entry["no_live_output"])
                    self.assertGreaterEqual(entry["verified_quote_count"], 2)
                    self.assertEqual(set(entry["prompts"]), set(pilot.ARMS))
                    for arm in pilot.ARMS:
                        messages = entry["prompts"][arm]["messages"]
                        self.assertEqual([m["role"] for m in messages],
                                         ["system", "user"])
                        self.assertNotIn(fixture["prior"], messages[0]["content"])
                        self.assertNotIn(fixture["current"], messages[0]["content"])
                        self.assertNotIn('"oracle"', messages[1]["content"])
                        self.assertNotIn("typed_jef_candidate", messages[1]["content"])
                        self.assertFalse(entry["prompts"][arm]["output_committed"])
                    raw = json.loads(entry["prompts"][pilot.ARMS[0]]["messages"][1]["content"])
                    spans = json.loads(entry["prompts"][pilot.ARMS[1]]["messages"][1]["content"])
                    body = json.loads(entry["prompts"][pilot.ARMS[2]]["messages"][1]["content"])
                    self.assertEqual([x["text"] for x in raw["sources"]],
                                     [fixture["prior"], fixture["current"]])
                    self.assertEqual([x["text"] for x in spans["spans"]],
                                     [fixture["policy_span"], fixture["option_span"]])
                    self.assertNotIn("sources", body)
                    self.assertNotIn("body_observations", body)
                    self.assertTrue(body["body_hypotheses_not_forwarded"])
                    self.assertFalse(body["quote_semantic_truth_authority"])
                    self.assertTrue(any(fixture["policy_span"] in q["text"]
                                        for q in body["verified_quotes"]))
                    self.assertTrue(any(fixture["option_span"] in q["text"]
                                        for q in body["verified_quotes"]))
            self.assertEqual(json.loads((out / "report.json").read_text()), report)

    def test_existing_work_path_refused_without_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            work, out = Path(d) / "work", Path(d) / "out"
            work.mkdir()
            with self.assertRaises(FileExistsError):
                pilot.run(FIXTURE, work, out)


if __name__ == "__main__":
    unittest.main()
