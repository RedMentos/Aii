"""Run87 new disjoint cohort, frozen strict scorer and budget preflight."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

try:
    from scripts import jef_b1b2_budget_fixture_877 as f
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import jef_b1b2_budget_fixture_877 as f


class Run87BudgetFixtureTests(unittest.TestCase):
    def test_01_registered_table_digest(self):
        digest = hashlib.sha256(json.dumps(
            f.TABLE, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(digest, f.TABLE_SHA256)
        self.assertEqual(f.SEED, 877)

    def test_02_six_disjoint_projects_and_balanced_oracle(self):
        rows = f.fixtures()
        self.assertEqual(len(rows), 6)
        self.assertEqual([x["project"] for x in rows],
                         ["Quartz", "Rowan", "Sable", "Tundra", "Umber", "Vesper"])
        self.assertFalse(set(x["project"] for x in rows)
                         & {"Alder", "Birch", "Cedar", "Dune", "Elm", "Fir",
                            "Juniper", "Kestrel", "Linden", "Mistral", "Nacre", "Orchid"})
        self.assertEqual([x["action"] for x in rows],
                         ["A", "B", "NONE", "A", "B", "NONE"])
        self.assertEqual([x["remaining"] for x in rows],
                         [30, 15, None, 45, 15, None])

    def test_03_paired_arm_order_counterbalanced(self):
        self.assertEqual([x["arm_order"][0] for x in f.fixtures()],
                         ["SHORT_96", "LONG_160"] * 3)
        self.assertEqual(f.OBSERVER_TOKENS, {"SHORT_96": 96, "LONG_160": 160})
        self.assertEqual(6 * len(f.ARMS) * len(f.ROLES) * 2, 48)

    def test_04_source_policy_only_in_prior(self):
        for row in f.fixtures():
            self.assertIn("Maximum budget:", row["prior"])
            self.assertIn("Maximum deadline:", row["prior"])
            self.assertNotIn("Maximum budget:", row["current"])
            self.assertNotIn("Maximum deadline:", row["current"])
            self.assertIn("Which option meets the archived policy?", row["current"])
            self.assertEqual(f.sha(row["prior"].encode()), row["source_sha256"]["prior"])
            self.assertEqual(f.sha(row["current"].encode()), row["source_sha256"]["current"])

    def test_05_budget_schema_caps_reproduced(self):
        self.assertEqual(f.QUOTE_MIN_CHARS, 80)
        self.assertEqual(f.summary_cap(96), 48)
        self.assertEqual(f.summary_cap(160), 84)
        self.assertGreater(f.summary_cap(256), 84)

    def test_06_tampered_table_rejected(self):
        changed = list(f.TABLE)
        row = list(changed[0]);row[1] += 1;changed[0] = tuple(row)
        with patch.object(f, "TABLE", tuple(changed)):
            with self.assertRaisesRegex(ValueError, "TABLE_HASH_RED"):
                f.fixtures()

    def test_07_wrong_oracle_rejected(self):
        changed = list(f.TABLE)
        row = list(changed[1]);row[-2] = "A";changed[1] = tuple(row)
        with patch.object(f, "TABLE", tuple(changed)), patch.object(
                f, "TABLE_SHA256", f.sha(json.dumps(tuple(changed),
                sort_keys=True, separators=(",", ":")).encode())):
            with self.assertRaisesRegex(ValueError, "BALANCE_RED"):
                f.fixtures()

    def test_08_registered_signal_boundary(self):
        scores = {role: {"SHORT_96": 1, "LONG_160": 3} for role in f.ROLES}
        self.assertEqual(f.verdict(scores, 3), "BUDGET_LONG_SMALL_SIGNAL_SHADOW")
        self.assertEqual(f.verdict(scores, 2), "BUDGET_NONINFERIOR_SHADOW")

    def test_09_registered_noninferior_and_red(self):
        scores = {role: {"SHORT_96": 0, "LONG_160": 0} for role in f.ROLES}
        self.assertEqual(f.verdict(scores, 0), "BUDGET_NONINFERIOR_SHADOW")
        scores["B1_DETAIL"]["SHORT_96"] = 2
        self.assertEqual(f.verdict(scores, 0), "BUDGET_UTILITY_RED")

    def test_10_score_shape_and_bool_rejected(self):
        with self.assertRaisesRegex(ValueError, "SCORE_SHAPE_RED"):
            f.verdict({}, 0)
        with self.assertRaisesRegex(ValueError, "SCORE_SHAPE_RED"):
            f.verdict({role: {arm: 0 for arm in f.ARMS} for role in f.ROLES}, True)
        bad = {role: {arm: 0 for arm in f.ARMS} for role in f.ROLES}
        bad["B1_DETAIL"]["LONG_160"] = True
        with self.assertRaisesRegex(ValueError, "ARM_SCORE_RED"):
            f.verdict(bad, 0)

    def test_11_native_pins_are_immutable_strings(self):
        for digest in (f.B1_SHA256, f.B2_SHA256, f.RUNNER_SHA256):
            self.assertEqual(len(digest), 64)
            int(digest, 16)

    def test_12_frozen_run77_strict_scorer_unchanged(self):
        try:
            from scripts.jef_b1b2_context_fixture_797 import strict_summary as old
        except ImportError:
            self.skipTest("frozen Run77 scorer module only available in full repository")
        for action, rem, text in (
            ("A", 30, "Choose option A. 30 credits remaining."),
            ("B", 15, "Option B is recommended; remaining 15 credits."),
            ("NONE", None, "Neither option qualifies."),
        ):
            self.assertEqual(f.strict_summary(text, action, rem), old(text, action, rem))
            self.assertEqual(f.strict_summary(text, action, rem), 1)
        self.assertEqual(f.strict_summary("Option A", "A", 30), 0)

if __name__ == "__main__":
    unittest.main()
