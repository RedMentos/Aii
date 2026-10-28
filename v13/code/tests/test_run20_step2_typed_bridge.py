"""Run20 exact-source typed bridge software-only acceptance and counterexamples."""
from collections import Counter
import copy
import unittest

from scripts import run18_step2_balanced_controls as balanced
from scripts import run20_step2_typed_bridge as bridge


def inputs(x):
    return {k: x[k] for k in ("id", "language", "type", "history", "current", "temporal_mode")}


class TypedBridge(unittest.TestCase):
    def test_all_balanced_cases_without_oracle_or_models(self):
        results = []
        for x in balanced.FIXTURES:
            with self.subTest(case=x["id"]):
                inp = inputs(x)
                self.assertNotIn("oracle", inp)
                self.assertNotIn("rules", inp)
                got = bridge.evaluate(inp)
                self.assertEqual(got["action"], x["oracle"]["action"])
                self.assertEqual(got["options"], x["oracle"]["options"])
                self.assertFalse(got["authority"])
                self.assertEqual(got["status"], "SOFTWARE_SOURCE_ONLY")
                self.assertEqual(len(got["source_sha256"]), 3)
                self.assertNotIn("oracle", got)
                results.append(got)
        self.assertEqual(Counter(x["action"] for x in results), {"A": 2, "B": 2, "NONE": 2})

    def test_reject_oracle_as_input(self):
        x = balanced.FIXTURES[0]
        with self.assertRaises(bridge.Refusal): bridge.evaluate(dict(inputs(x), oracle=x["oracle"]))

    def test_no_prior_rules_or_options_fails_closed(self):
        for x in balanced.FIXTURES:
            if x["type"] != "SPLIT": continue
            inp = copy.deepcopy(inputs(x))
            inp["history"][0] = ("Projekt " if x["language"] == "DE" else "Project ")+x["id"]+" no binding rules."
            with self.assertRaises((bridge.Refusal, ValueError)):
                bridge.evaluate(inp)
            inp = copy.deepcopy(inputs(x))
            inp["history"][2] = ("Projekt " if x["language"] == "DE" else "Project ")+x["id"]+" supplier sheet, options unavailable."
            with self.assertRaises((bridge.Refusal, ValueError)):
                bridge.evaluate(inp)

    def test_cross_project_sheet_and_temporal_spoof_refuse(self):
        for x in balanced.FIXTURES:
            inp = copy.deepcopy(inputs(x))
            if x["type"] in ("SPLIT", "REVISION"):
                inp["history"][2] += " Project Quasar archive."
                with self.assertRaises((bridge.Refusal, ValueError)):
                    bridge.evaluate(inp)
            inp = copy.deepcopy(inputs(x))
            inp["temporal_mode"] = "RETAIN_PRIOR_RULES" if x["type"] == "REVISION" else "REVISED_CURRENT_RULES"
            with self.assertRaises((bridge.Refusal, ValueError)):
                bridge.evaluate(inp)


if __name__ == "__main__": unittest.main()
