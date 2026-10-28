"""Run15 RED-first: fresh source-disjoint bilingual STEP2 fixture contract."""
import hashlib
import json
import unittest
from collections import Counter

from scripts import step2_longnote_revision_fixtures as original
from scripts import run15_step2_disjoint_bilingual_fixtures as fresh
from v13.agi.eligibility import recipe


def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


class FreshStep2BilingualFixtures(unittest.TestCase):
    def test_six_unique_names_and_no_original_cohort_reuse(self):
        fixtures = fresh.FIXTURES
        self.assertEqual(len(fixtures), 6)
        names = [x["id"] for x in fixtures]
        self.assertEqual(len(names), len(set(names)))
        self.assertFalse(set(names) & {x["id"] for x in original.FIXTURES})
        self.assertNotIn("Atlas", names)
        self.assertEqual(Counter(x["language"] for x in fixtures), {"EN": 3, "DE": 3})
        self.assertEqual(Counter(x["type"] for x in fixtures), {"SPLIT": 2, "RULE": 2, "REVISION": 2})

    def test_old_rule_source_within_b2_excerpt_and_long_note(self):
        for x in fresh.FIXTURES:
            old = x["history"][0]
            self.assertGreater(len(old), 400)
            excerpt = old[:240]
            self.assertIn(str(x["old_rules"]["budget"]), excerpt)
            self.assertIn(str(x["old_rules"]["deadline"]), excerpt)
            self.assertIn("Budget", excerpt)
            self.assertIn("Frist" if x["language"] == "DE" else "Deadline", excerpt)
            self.assertEqual(x["source_contract"]["b2_excerpt_chars"], 240)

    def test_recent_sheet_options_are_after_b2_window(self):
        for x in fresh.FIXTURES:
            self.assertEqual(len(x["history"]), 3)
            if x["type"] in ("SPLIT", "REVISION"):
                sheet = x["history"][2]
                self.assertGreater(x["source_contract"]["sheet_options_start"], 240)
                self.assertNotIn("Option A:", sheet[:240])
                self.assertIn("Option A:", sheet[240:])
                self.assertIn("Option B:", sheet[240:])
            else:
                self.assertIn("Option A:", x["current"])
                self.assertIn("Option B:", x["current"])

    def test_unrelated_project_and_temporal_modes(self):
        for x in fresh.FIXTURES:
            self.assertIn("Quasar", x["history"][1])
            self.assertNotIn(x["id"], x["history"][1])
            self.assertIn(x["id"], x["current"])
            self.assertNotIn("oracle", " ".join(x["history"] + [x["current"]]).lower())
            self.assertNotIn("answer:", " ".join(x["history"] + [x["current"]]).lower())
            self.assertEqual(x["temporal_mode"], "REVISED_CURRENT_RULES" if x["type"] == "REVISION" else "RETAIN_PRIOR_RULES")
            if x["type"] == "REVISION":
                self.assertNotEqual(x["rules"], x["old_rules"])

    def test_oracle_matches_independent_recipe(self):
        for x in fresh.FIXTURES:
            opts = x["source_contract"]["options"]
            expected = [{"entity": k, "cost": v[0], "days": v[1], "local": v[2]}
                        for k, v in (("A", opts[0]), ("B", opts[1]))]
            rules = x["rules"]
            action, details = recipe(rules["budget"], rules["deadline"], rules["local_only"], expected)
            self.assertEqual(x["oracle"], {"project": x["id"], "action": action, "options": details})

    def test_german_and_english_rule_intent_are_explicit(self):
        for x in fresh.FIXTURES:
            if x["language"] == "DE":
                self.assertIn("Projekt ", x["current"])
                self.assertIn("früheren", x["current"] if x["type"] != "REVISION" else "früheren")
                if x["type"] == "REVISION":
                    self.assertIn("Aktuelle verbindliche Regeln", x["current"])
            else:
                self.assertIn("Project ", x["current"])
                if x["type"] != "REVISION": self.assertIn("earlier", x["current"])

    def test_fixture_hash_stable_and_no_authority(self):
        self.assertEqual(fresh.FIXTURE_SHA256, hashlib.sha256(canonical(fresh.FIXTURES)).hexdigest())
        self.assertEqual(fresh.SEEDS, (20261114, 20261115, 20261116))
        self.assertFalse(fresh.CANONICAL_GATE_PASS)
        self.assertEqual(fresh.JEPA_WEIGHT, 0)

    def test_reject_duplicate_and_original_names(self):
        with self.assertRaises(ValueError):
            fresh.build_cases((fresh.CASES[0], fresh.CASES[0]))
        with self.assertRaises(ValueError):
            bad = list(fresh.CASES[0]); bad[0] = "Aquila"
            fresh.build_cases((tuple(bad),))


if __name__ == "__main__":
    unittest.main()
