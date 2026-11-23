"""STEP2 long-note/revision corpus structural preflight; software only."""
import copy
import unittest
from collections import Counter

from scripts import step2_z2_timescale as z2
from scripts.step2_longnote_revision_fixtures import (
    CASES, FIXTURES, REVISION, long_kickoff, recent_sheet)
from v13.agi.eligibility import recipe, stated, option_stated, stated_values
from v13.cognition import quote_span, quote_choices


class LongNoteRevisionFixtures(unittest.TestCase):
    def test_new_disjoint_deterministic_cohort_does_not_mutate_frozen_z2(self):
        original = copy.deepcopy(z2.FIXTURES)
        self.assertEqual(REVISION, "step2-longnote-revision-fixtures-v1")
        self.assertEqual(len(FIXTURES), 10)
        self.assertEqual(Counter(f["type"] for f in FIXTURES),
                         Counter({"SPLIT": 3, "RULE": 3, "DETAIL": 3, "REVISION": 1}))
        self.assertEqual(len({f["id"] for f in FIXTURES}), 10)
        # Prevent a trivial always-A policy from looking useful.
        self.assertEqual(Counter(f["oracle"]["action"] for f in FIXTURES),
                         Counter({"A": 4, "B": 4, "NONE": 2}))
        self.assertFalse({f["id"] for f in FIXTURES} & {f["id"] for f in original})
        from tests import integration_step2_utility as baseline_step2
        self.assertFalse({f["id"] for f in FIXTURES}
                         & {f["id"] for f in baseline_step2.FIXTURES})
        self.assertFalse({f["old_rules"]["budget"] for f in FIXTURES}
                         & {f["rules"]["budget"] for f in original})
        self.assertEqual(z2.FIXTURES, original)
        self.assertEqual([f["id"] for f in FIXTURES],
                         [case[0] for case in CASES])

    def test_long_notes_expose_rules_in_b2_first_240_but_not_heading_200(self):
        for name, kind, old, a, b, revised in CASES:
            with self.subTest(name=name):
                note = long_kickoff(name, old)
                self.assertGreater(len(note), 400)
                expected = dict(zip(("budget", "deadline", "local_only"), old))
                self.assertTrue(all(stated(k, v, note) for k, v in expected.items()))
                self.assertTrue(all(stated(k, v, note[:240]) for k, v in expected.items()))
                self.assertFalse(all(stated(k, v, note[:200]) for k, v in expected.items()))
                # Exercise the actual pointer/quote expansion, not merely a
                # naive prefix slice. One heading choice must not carry all
                # three rule values through the 200-char source expansion.
                first = quote_choices([note])[0]
                self.assertEqual(first[0], 0)
                heading = note[first[1]:first[2]]
                span = quote_span(heading, note, 200)
                self.assertIsNotNone(span)
                expanded = note[span[0]:span[1]]
                self.assertFalse(all(stated(k, v, expanded) for k, v in expected.items()))
                self.assertEqual(FIXTURES[[x["id"] for x in FIXTURES].index(name)]["old_rules"],
                                 expected)

    def test_options_and_rules_are_source_visible_only_in_intended_lanes(self):
        for f, (_, kind, old, a, b, revised) in zip(FIXTURES, CASES):
            with self.subTest(kind=kind, name=f["id"]):
                self.assertEqual(len(f["history"]), 3)
                options = f["oracle"]["options"]
                self.assertEqual({x["entity"] for x in options}, {"A", "B"})
                if kind in ("SPLIT", "DETAIL", "REVISION"):
                    self.assertGreater(f["history"][2].find("Option A:"), 240)
                    self.assertTrue(all(option_stated(o, [f["history"][2]]) for o in options))
                    self.assertFalse(any(option_stated(o, [f["current"]]) for o in options))
                else:
                    self.assertTrue(all(option_stated(o, [f["current"]]) for o in options))
                if kind in ("SPLIT", "RULE"):
                    self.assertTrue(all(stated(k, v, f["history"][0])
                                        for k, v in f["rules"].items()))
                    self.assertFalse(any(stated_values(k, f["current"])
                                         for k in ("budget", "deadline", "local_only")))
                elif kind == "DETAIL":
                    self.assertTrue(all(stated(k, v, f["current"])
                                        for k, v in f["rules"].items()))
                    self.assertFalse(any(stated_values(k, f["history"][0])
                                         for k in ("budget", "deadline", "local_only")))
                else:
                    self.assertEqual(kind, "REVISION")
                    self.assertNotEqual(f["old_rules"], f["rules"])
                    self.assertEqual(f["temporal_mode"], "REVISED_CURRENT_RULES")
                    self.assertTrue(all(stated(k, v, f["current"])
                                        for k, v in f["rules"].items()))
                    self.assertTrue(all(stated(k, v, f["history"][0])
                                        for k, v in f["old_rules"].items()))

    def test_oracle_matches_independent_recipe_and_revision_precedence(self):
        for f, (_, kind, old, a, b, revised) in zip(FIXTURES, CASES):
            with self.subTest(name=f["id"]):
                rules = revised if revised is not None else old
                opts = [{"entity": e, "cost": o[0], "days": o[1], "local": o[2]}
                        for e, o in (("A", a), ("B", b))]
                action, expected = recipe(*rules, opts)
                eligible = [o for o in opts if o["cost"] <= rules[0]
                            and o["days"] <= rules[1]
                            and (o["local"] or not rules[2])]
                manual_action = (min(eligible, key=lambda o: (o["cost"], o["entity"]))["entity"]
                                 if eligible else "NONE")
                self.assertEqual(action, manual_action)
                self.assertEqual(f["oracle"]["action"], action)
                self.assertEqual(f["oracle"]["options"], expected)
                if kind == "REVISION":
                    old_action, _ = recipe(*old, opts)
                    self.assertNotEqual(old_action, action,
                                        "Revision fixture must distinguish old and new action")

    def test_invalid_kind_and_revision_contract_reject(self):
        from scripts.step2_longnote_revision_fixtures import fixture
        row = CASES[0]
        with self.assertRaises(ValueError):
            fixture(row[0], "UNKNOWN", row[2], row[3], row[4])
        with self.assertRaises(ValueError):
            fixture(row[0], "REVISION", row[2], row[3], row[4])
        with self.assertRaises(ValueError):
            fixture(row[0], "SPLIT", row[2], row[3], row[4], (200, 9, False))


if __name__ == "__main__":
    unittest.main()
