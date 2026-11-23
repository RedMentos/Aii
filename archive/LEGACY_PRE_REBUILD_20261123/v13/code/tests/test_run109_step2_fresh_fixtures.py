"""Run109: fresh STEP2 long/revised fixture generator, no native or gate promotion."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts import step2_z2_timescale as z2
from scripts.run109_step2_fresh_fixtures import (
    canonical_sha256, fixtures, inspect, main,
)


class FreshStep2Fixtures(unittest.TestCase):
    def test_registered_six_fixed_new_projects_and_no_old_mutation(self):
        original = canonical_sha256(z2.FIXTURES)
        cases = fixtures()
        self.assertEqual([f["id"] for f in cases],
                         ["Atlas", "Borealis", "Cygnus", "Delta", "Epsilon", "Fornax"])
        self.assertEqual(len(set(f["id"] for f in cases)), 6)
        self.assertEqual(canonical_sha256(z2.FIXTURES), original)
        self.assertFalse(set(f["id"] for f in cases).intersection(
            f["id"] for f in z2.FIXTURES))

    def test_long_rules_beyond_b2_excerpt_and_latest_oracles(self):
        for f in fixtures()[:3]:
            with self.subTest(project=f["id"]):
                self.assertEqual(f["fixture_kind"], "LONG")
                self.assertGreaterEqual(f["history"][0].index("Budget "), 240)
                self.assertEqual(f["rules"]["budget"],
                                 {"Atlas": 130, "Borealis": 95, "Cygnus": 115}[f["id"]])

    def test_revisions_are_ordered_and_latest_rules_in_oracle(self):
        for f in fixtures()[3:]:
            with self.subTest(project=f["id"]):
                self.assertEqual(f["fixture_kind"], "REVISED")
                self.assertNotEqual(f["old_rules"], f["rules"])
                self.assertIn("Historical rules (superseded)", f["history"][0])
                self.assertIn("revision (later than kickoff)", f["history"][1])
                self.assertEqual(f["oracle"]["project"], f["id"])
                self.assertEqual(f["rules"]["budget"],
                                 {"Delta": 100, "Epsilon": 90, "Fornax": 110}[f["id"]])

    def test_closed_deterministic_report_and_negative_gates(self):
        first = inspect()
        second = inspect()
        self.assertEqual(first["fixture_sha256"], second["fixture_sha256"])
        self.assertEqual(first["status"], "FRESH_FIXTURES_READY_SOFTWARE_ONLY")
        self.assertTrue(all(first["checks"].values()))
        self.assertFalse(first["canonical_gate_pass"])
        self.assertEqual(first["step2_status"], "UTILITY_FAIL")
        self.assertFalse(first["model_called"])
        self.assertEqual(first["native_calls"], 0)

    def test_report_requires_fresh_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run109-report.json"
            self.assertEqual(main(["--out", str(out)]), 0)
            self.assertEqual(json.loads(out.read_text())["count"], 6)
            with self.assertRaises(FileExistsError):
                main(["--out", str(out)])


if __name__ == "__main__":
    unittest.main()
