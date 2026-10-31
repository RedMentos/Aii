"""Run115J frozen seed997 real Store JEF->C3 typed-vs-raw model-free proof."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.run115j_typed_jef_role_native import (
    ARMS, EXPECTED, FIXTURE_SHA, fixture, run,
)
from v13.common import file_hash

FIXTURE = Path(__file__).parents[1] / "docs/fixtures/RUN115J_TYPED_JEF_ROLE_SEED997.json"


class Run115JNativePreflightTests(unittest.TestCase):
    def test_fixture_exact_hash_and_balanced_oracles(self):
        self.assertEqual(file_hash(FIXTURE), FIXTURE_SHA)
        rows = fixture(FIXTURE)
        self.assertEqual(len(rows), 6)
        self.assertEqual(
            [(x["oracle"]["choice"], x["oracle"]["remaining"]) for x in rows],
            list(EXPECTED))
        self.assertEqual([x["oracle"]["choice"] for x in rows].count("NONE"), 2)

    def test_tampered_fixture_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.json"
            p.write_text(FIXTURE.read_text().replace("Kairo", "Kairox", 1))
            with self.assertRaisesRegex(ValueError, "FROZEN_FIXTURE_SHA"):
                fixture(p)

    def test_six_real_store_jef_typed_and_raw_prompts_without_native(self):
        with tempfile.TemporaryDirectory() as d:
            report = run(FIXTURE, Path(d) / "work", Path(d) / "out")
            self.assertEqual(report["status"], "MODEL_FREE_SIX_CASE_PREFLIGHT_PASS")
            self.assertEqual(report["native_c3_calls"], 0)
            self.assertEqual(report["native_jef_calls"], 0)
            self.assertEqual(report["native_b1_calls"], 0)
            self.assertEqual(report["native_b2_calls"], 0)
            self.assertEqual(len(report["rows"]), 6)
            for recorded, row in zip(report["rows"], fixture(FIXTURE)):
                self.assertTrue(recorded["closed_store_ok"])
                self.assertTrue(recorded["no_live_output"])
                self.assertEqual(recorded["typed_jef_candidate"], row["oracle"])
                self.assertEqual(len(recorded["context_plan_packet_ids"]), 2)
                self.assertEqual({a["arm"] for a in recorded["arms"]}, set(ARMS))
                for a in recorded["arms"]:
                    messages = a["messages"]
                    self.assertEqual([m["role"] for m in messages],
                                     ["system", "user"])
                    self.assertNotIn(row["prior"], messages[0]["content"])
                    self.assertNotIn(row["current"], messages[0]["content"])
                    self.assertNotIn('"oracle"', json.dumps(messages))
                    payload = json.loads(messages[1]["content"])
                    self.assertIn(row["prior"], messages[1]["content"])
                    self.assertIn(row["current"], messages[1]["content"])
                    if a["arm"] == "TYPED_JEF_ROLE":
                        self.assertEqual(payload["typed_jef_candidate"],
                                         row["oracle"])
                        self.assertEqual(payload["typed_candidate_authority"], 0)
                    else:
                        self.assertNotIn("typed_jef_candidate", payload)
                    self.assertEqual(a["status"], "MODEL_FREE_PROMPT_VERIFIED")
            self.assertEqual(report["learning_authority"], 0)
            self.assertEqual(report["delivery_authority"], 0)
            self.assertFalse(report["output_committed"])

    def test_fresh_work_and_report_required(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d) / "work"
            out = Path(d) / "out"
            run(FIXTURE, work, out)
            with self.assertRaisesRegex(FileExistsError, "FRESH_WORK"):
                run(FIXTURE, work, out)


if __name__ == "__main__":
    unittest.main()
