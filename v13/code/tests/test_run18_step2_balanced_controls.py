"""Run18 preregistered balanced controls and original cohort non-mutation."""
from collections import Counter
import hashlib
import json
import unittest

from scripts import run18_step2_balanced_controls as b
from scripts import run15_step2_disjoint_bilingual_fixtures as run15
from scripts import step2_longnote_revision_fixtures as tp27


class BalancedControls(unittest.TestCase):
    def test_balanced_label_language_type_and_frozen_original(self):
        self.assertEqual(len(b.FIXTURES), 6)
        self.assertEqual(Counter(x["oracle"]["action"] for x in b.FIXTURES),
                         {"A": 2, "B": 2, "NONE": 2})
        self.assertEqual(Counter(x["language"] for x in b.FIXTURES), {"EN": 3, "DE": 3})
        self.assertEqual(Counter(x["type"] for x in b.FIXTURES),
                         {"SPLIT": 2, "RULE": 2, "REVISION": 2})
        names = {x["id"] for x in b.FIXTURES}
        self.assertFalse(names & {x["id"] for x in run15.FIXTURES})
        self.assertFalse(names & {x["id"] for x in tp27.FIXTURES})
        self.assertEqual(run15.FIXTURE_SHA256, hashlib.sha256(json.dumps(
            run15.FIXTURES, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest())

    def test_always_a_baseline_exposes_original_confound(self):
        self.assertEqual(b.RUN15_ALWAYS_A, {"correct": 5, "total": 6})
        self.assertEqual(b.RUN18_ALWAYS_A, {"correct": 2, "total": 6})
        self.assertEqual(sum(x["oracle"]["action"] == "A" for x in run15.FIXTURES
                             if x["language"] == "DE"), 3)
        for language in ("EN", "DE"):
            self.assertEqual(Counter(x["oracle"]["action"] for x in b.FIXTURES
                                     if x["language"] == language),
                             {"A": 1, "B": 1, "NONE": 1})

    def test_independent_oracle_and_no_source_leakage(self):
        for x in b.FIXTURES:
            with self.subTest(case=x["id"]):
                rules = x["rules"]
                eligible = []
                expected = []
                for entity, triple in zip("AB", x["source_contract"]["options"]):
                    cost, days, local = triple
                    ok = (cost <= rules["budget"] and days <= rules["deadline"]
                          and (local or not rules["local_only"]))
                    expected.append({"entity": entity, "cost": cost,
                                     "remaining": rules["budget"] - cost,
                                     "days": days, "local": local, "eligible": ok})
                    if ok: eligible.append((cost, entity))
                choice = min(eligible)[1] if eligible else "NONE"
                self.assertEqual(x["oracle"], {"project": x["id"],
                                               "action": choice, "options": expected})
                source = " ".join(x["history"] + [x["current"]]).lower()
                self.assertNotIn("oracle", source)
                self.assertNotIn("answer:", source)
                self.assertIn(str(x["old_rules"]["budget"]), x["history"][0][:240])
                self.assertIn(str(x["old_rules"]["deadline"]), x["history"][0][:240])
                if x["type"] in ("SPLIT", "REVISION"):
                    self.assertNotIn("Option A:", x["history"][2][:240])
                    self.assertIn("Option A:", x["history"][2][240:])
                else:
                    self.assertIn("Option A:", x["current"])
                self.assertEqual(x["temporal_mode"],
                                 "REVISED_CURRENT_RULES" if x["type"] == "REVISION"
                                 else "RETAIN_PRIOR_RULES")

    def test_hash_seeds_no_authority(self):
        self.assertEqual(b.FIXTURE_SHA256, hashlib.sha256(json.dumps(
            b.FIXTURES, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest())
        self.assertEqual(b.SEEDS, (20261201, 20261202, 20261203))
        self.assertFalse(b.GATE_PASS)

    def test_reject_imbalanced_or_original_cases(self):
        with self.assertRaises(ValueError): b.build_controls(run15.CASES)
        bad = list(b.CASES)
        row = list(bad[1])
        row[4] = (145, 10, True)
        bad[1] = tuple(row)
        with self.assertRaises(ValueError): b.build_controls(tuple(bad))
        with self.assertRaises(ValueError): b.build_controls(b.CASES[:5])


if __name__ == "__main__": unittest.main()
