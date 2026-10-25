"""Run394 preregistered fresh STEP2 fixture and control-arm invariants, no models."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run394_step2_fresh as r


class Run394FreshFixtures(unittest.TestCase):
    def test_six_new_cases_and_oracles(self):
        self.assertEqual([f["id"] for f in r.FIXTURES], ["Alder", "Beacon", "Cypress", "Delta", "Ember", "Fable"])
        self.assertTrue(r.validate_fixtures(r.FIXTURES))
        self.assertEqual({f["id"]: f["oracle"]["action"] for f in r.FIXTURES},
                         {"Alder": "A", "Beacon": "B", "Cypress": "B",
                          "Delta": "B", "Ember": "A", "Fable": "NONE"})

    def test_exact_b2_note_and_b1_sheet_boundaries(self):
        for f in r.FIXTURES:
            with self.subTest(fixture=f["id"]):
                old = f["old_rules"]
                phrase = r.rule_text((old["budget"], old["deadline"], old["local_only"]))
                start = f["history"][0].index(phrase)
                self.assertGreaterEqual(start, 140)
                self.assertLess(start, 200)
                self.assertGreater(start + len(phrase), 200)
                self.assertLessEqual(start + len(phrase), 240)
                opt = f["history"][2].index("Option A:")
                self.assertGreater(opt, 240)
                self.assertLess(opt, 600)
                self.assertNotIn("Option A:", f["history"][0])
                self.assertNotIn(phrase, f["history"][1])

    def test_revisions_override_old_rules_in_current_source(self):
        for f in r.FIXTURES:
            if f["revision_case"]:
                self.assertNotEqual(f["rules"], f["old_rules"])
                self.assertIn("supersedes", f["current"])
                for field in ("budget", "deadline", "local_only"):
                    self.assertIn(str(f["rules"][field]).lower(), f["current"].lower())
            else:
                self.assertEqual(f["rules"], f["old_rules"])
                self.assertNotIn("supersedes", f["current"])

    def test_mutated_or_truncated_source_is_rejected(self):
        f = copy.deepcopy(r.FIXTURES[0])
        f["history"][0] = f["history"][0][:180]
        with self.assertRaises(ValueError):
            r.validate_fixtures([f])
        f = copy.deepcopy(r.FIXTURES[0])
        f["history"][2] = f["history"][2][:200]
        with self.assertRaises(ValueError):
            r.validate_fixtures([f])
        f = copy.deepcopy(r.FIXTURES[3])
        f["rules"] = f["old_rules"]
        with self.assertRaises(ValueError):
            r.validate_fixtures([f])

    def test_preregistered_arms_and_seeds_include_shared_body_pointer(self):
        self.assertEqual(r.SEEDS, (20, 21, 22))
        self.assertEqual(r.ARMS["O"], {"base": "C", "query": True, "pointer": "off"})
        self.assertEqual(r.ARMS["P"], {"base": "C", "query": True, "pointer": "pointer"})
        self.assertEqual(r.ARMS["S"], {"base": "D", "query": True, "pointer": "pointer"})
        self.assertEqual(r.PILOT_IDS, ("Alder", "Delta"))

    def test_manifest_deterministic_nonpromoting_and_hash_bound(self):
        f = [x for x in r.FIXTURES if x["id"] in r.PILOT_IDS]
        a = r.manifest(f, True, ["O", "P", "S"], [20])
        b = r.manifest(f, True, ["O", "P", "S"], [20])
        self.assertEqual(a, b)
        self.assertFalse(a["canonical_gate_pass"])
        self.assertEqual(a["step2_exit"], "UTILITY_FAIL")
        self.assertEqual(a["stage"], "PILOT")
        self.assertEqual(a["fixture_ids"], ["Alder", "Delta"])
        self.assertEqual(a["fixture_sha256"],
                         hashlib.sha256(json.dumps(f, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
        self.assertEqual(a["source_sha256"]["run394_script"], r.file_sha(r.__file__))

    def test_configure_only_private_modules_not_original_fixtures(self):
        import step2_z2_timescale as z2
        import step2_z2c_b2_rule as z2c
        original_copy = copy.deepcopy(z2.FIXTURES)
        prior = (z2.FIXTURES, z2c.FIX, z2c.RULE_EPISODES,
                 dict(z2c.ARMS), dict(z2c.z2b.ARMS), z2c.SEEDS, z2c.z2b.SEEDS)
        selected = [x for x in r.FIXTURES if x["id"] in r.PILOT_IDS]
        try:
            configured = r.configure(selected)
            self.assertEqual(set(configured.FIX), set(r.PILOT_IDS))
            self.assertEqual(configured.z2b.ARMS["S"]["base"], "D")
            self.assertEqual(configured.ARMS["S"], "pointer")
            self.assertEqual(len(original_copy), 10)
            self.assertEqual(len(selected), 2)
        finally:
            z2.FIXTURES, z2c.FIX, z2c.RULE_EPISODES = prior[:3]
            z2c.ARMS.clear()
            z2c.ARMS.update(prior[3])
            z2c.z2b.ARMS.clear()
            z2c.z2b.ARMS.update(prior[4])
            z2c.SEEDS, z2c.z2b.SEEDS = prior[5:]
        self.assertEqual(z2.FIXTURES, original_copy)
        self.assertEqual(hashlib.sha256((ROOT / "scripts/step2_z2_timescale.py").read_bytes()).hexdigest(),
                         r.file_sha(ROOT / "scripts/step2_z2_timescale.py"))


if __name__ == "__main__":
    unittest.main()
