"""Run115I frozen cohort / real SQLite Context OS model-free native preflight."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.run115i_c3_role_source_native import (
    ARMS, EXPECTED, FIXTURE_SHA, fixture, run,
)
from v13.common import file_hash

FIXTURE = Path(__file__).parents[1] / "docs/fixtures/RUN115I_C3_ROLE_SOURCE_SEED983.json"


class Run115IPreflightTests(unittest.TestCase):
    def test_fixture_is_exactly_hash_frozen_balanced(self):
        self.assertEqual(file_hash(FIXTURE), FIXTURE_SHA)
        rows = fixture(FIXTURE)
        self.assertEqual(len(rows), 6)
        self.assertEqual(
            [(x["oracle"]["choice"], x["oracle"]["remaining"]) for x in rows],
            list(EXPECTED))
        self.assertEqual(
            [x["oracle"]["choice"] for x in rows].count("NONE"), 2)

    def test_tampered_fixture_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "tampered.json"
            p.write_text(FIXTURE.read_text().replace("Vireo", "Virae", 1))
            with self.assertRaisesRegex(ValueError, "FROZEN_FIXTURE_SHA"):
                fixture(p)

    def test_real_store_role_bound_two_source_vs_current_only(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d) / "work"
            out = Path(d) / "out"
            report = run(FIXTURE, work, out)
            self.assertEqual(report["status"], "MODEL_FREE_SIX_CASE_PREFLIGHT_PASS")
            self.assertEqual(report["native_c3_calls"], 0)
            self.assertEqual(report["native_b1_calls"], 0)
            self.assertEqual(report["native_b2_calls"], 0)
            self.assertEqual(report["learning_authority"], 0)
            self.assertEqual(report["delivery_authority"], 0)
            self.assertFalse(report["whole_system_complete"])
            self.assertEqual(len(report["rows"]), 6)
            rows = fixture(FIXTURE)
            for recorded, source in zip(report["rows"], rows):
                self.assertTrue(recorded["closed_store_ok"])
                self.assertTrue(recorded["no_live_output"])
                self.assertEqual(recorded["status"], "MODEL_FREE_PREFLIGHT_PASS")
                self.assertEqual(len(recorded["arms"]), 2)
                self.assertEqual({x["arm"] for x in recorded["arms"]}, set(ARMS))
                for arm in recorded["arms"]:
                    messages = arm["messages"]
                    self.assertEqual([m["role"] for m in messages],
                                     ["system", "user"])
                    self.assertNotIn(source["prior"], messages[0]["content"])
                    self.assertNotIn(source["current"], messages[0]["content"])
                    self.assertNotIn('"oracle"', json.dumps(messages))
                    self.assertIn(source["current"], messages[1]["content"])
                    self.assertEqual(source["prior"] in messages[1]["content"],
                                     arm["arm"] == "FULL_TWO_SOURCE")
                    self.assertEqual(arm["status"], "MODEL_FREE_PROMPT_VERIFIED")
            self.assertEqual(json.loads((out / "report.json").read_text())
                             ["status"], report["status"])

    def test_fresh_evidence_directory_required(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d) / "work"
            out = Path(d) / "out"
            run(FIXTURE, work, out)
            with self.assertRaisesRegex(FileExistsError, "FRESH_WORK"):
                run(FIXTURE, work, out)


if __name__ == "__main__":
    unittest.main()
