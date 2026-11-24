"""Disjoint B2-source-exact × C3 input intervention; software-only prereg."""
import copy
import json
import unittest

from scripts import run33_b2_c3_counterfactual_envelopes as cf
from v13.agi import eligibility


class B2C3CounterfactualEnvelope(unittest.TestCase):
    def test_preregistered_balanced_disjoint_cohort(self):
        reg = cf.prereg()
        self.assertEqual(reg["fixtures"], 6)
        self.assertEqual(reg["languages"], {"EN": 3, "DE": 3})
        self.assertEqual(reg["oracle_action_balance"], {"A": 2, "B": 2, "NONE": 2})
        self.assertEqual(reg["seeds"], [20261121, 20261122, 20261123])
        self.assertIs(reg["canonical_gate_pass"], False)
        self.assertIs(reg["native_executed"], False)

    def test_all_arms_exact_quote_source_provenance(self):
        for fixture in cf.FIXTURES:
            for arm in cf.ARMS:
                with self.subTest(fixture=fixture["id"], arm=arm):
                    report = cf.build_envelope(fixture["id"], arm, cf.SEEDS[0])
                    self.assertTrue(cf.verify_envelope(report))
                    self.assertEqual(report["evidence_level"], "SYNTHETIC_SOURCE_ONLY_NO_C3")
                    self.assertIs(report["authority"], False)
                    self.assertIs(report["native_executed"], False)
                    self.assertIs(report["canonical_gate_pass"], False)
                    self.assertEqual(report["jepa_weight"], 0)
                    self.assertEqual(len(report["messages"]), 2)
                    context = json.loads(report["messages"][1]["content"])
                    self.assertEqual(set(context), {"current_source", "analysts"})
                    self.assertEqual(context["current_source"], fixture["current"])
                    quotes = [q for a in context["analysts"] for q in a["verified_quotes"]]
                    self.assertEqual(len(quotes), len(report["quote_provenance"]))
                    for quote, ref in zip(quotes, report["quote_provenance"]):
                        self.assertIn(ref["source_role"], ("old", "sheet"))
                        source = fixture["history"][0 if ref["source_role"] == "old" else 2]
                        self.assertEqual(source[ref["char_start"]:ref["char_end"]], quote)
                        self.assertEqual(len(quote), ref["char_end"] - ref["char_start"])

    def test_counterfactual_arms_are_controlled(self):
        for fixture in cf.FIXTURES:
            outputs = {arm: cf.build_envelope(fixture["id"], arm, cf.SEEDS[0])
                       for arm in cf.ARMS}
            contexts = {arm: json.loads(x["messages"][1]["content"])
                        for arm, x in outputs.items()}
            self.assertEqual(contexts["CURRENT_ONLY"]["analysts"], [])
            self.assertEqual(len(contexts["B1_ONLY"]["analysts"]), 1)
            self.assertEqual(contexts["B1_ONLY"]["analysts"],
                             contexts["B1_B2_MISSING"]["analysts"][:1])
            self.assertEqual(contexts["B1_B2_MISSING"]["analysts"][1]["verified_quotes"], [])
            self.assertEqual(contexts["B1_B2_EXACT"]["analysts"][:1],
                             contexts["B1_B2_MISSING"]["analysts"][:1])
            self.assertEqual(contexts["B1_B2_DISTRACTOR"]["analysts"][:1],
                             contexts["B1_B2_MISSING"]["analysts"][:1])
            exact = contexts["B1_B2_EXACT"]["analysts"][1]["verified_quotes"]
            distract = contexts["B1_B2_DISTRACTOR"]["analysts"][1]["verified_quotes"]
            self.assertEqual(len(exact), 1)
            self.assertEqual(len(distract), 1)
            self.assertNotEqual(exact, distract)
            self.assertFalse(all(eligibility.stated(k, v, distract[0])
                                 for k, v in fixture["old_rules"].items()))

    def test_no_oracle_or_scoring_fields_in_c3_user_payload(self):
        for fixture in cf.FIXTURES:
            for arm in cf.ARMS:
                report = cf.build_envelope(fixture["id"], arm, cf.SEEDS[1])
                context = json.loads(report["messages"][1]["content"])
                self.assertEqual(set(context), {"current_source", "analysts"})
                for analyst in context["analysts"]:
                    self.assertEqual(set(analyst), {"role", "hypothesis", "verified_quotes"})
                    self.assertEqual(analyst["hypothesis"], "SOURCE_EXACT")
                self.assertNotIn("oracle", report["messages"][1]["content"])
                self.assertNotIn("expected_action", report["messages"][1]["content"])
                self.assertNotIn("source_hashes", report["messages"][1]["content"])

    def test_invalid_case_arm_seed_refuse(self):
        for args in (("Keldara", cf.ARMS[0], cf.SEEDS[0]),
                     ("Velaris", "UNREGISTERED", cf.SEEDS[0]),
                     ("Velaris", cf.ARMS[0], 20261114),
                     ("Velaris", cf.ARMS[0], True)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                cf.build_envelope(*args)

    def test_tampered_envelope_refuses(self):
        original = cf.build_envelope("Velaris", "B1_B2_EXACT", cf.SEEDS[0])
        for change in ("quote", "source", "action", "role", "seed", "hash"):
            value = copy.deepcopy(original)
            context = json.loads(value["messages"][1]["content"])
            if change == "quote":
                context["analysts"][1]["verified_quotes"][0] += " forged"
                value["messages"][1]["content"] = json.dumps(context)
            elif change == "source":
                context["current_source"] = "Project Other."
                value["messages"][1]["content"] = json.dumps(context)
            elif change == "action":
                context["oracle"] = {"action": "A"}
                value["messages"][1]["content"] = json.dumps(context)
            elif change == "role":
                context["analysts"][1]["role"] = "B1_DETAIL"
                value["messages"][1]["content"] = json.dumps(context)
            elif change == "seed":
                value["seed"] = 20261114
            else:
                value["quote_provenance"][0]["source_sha256"] = "0" * 64
            with self.subTest(change=change), self.assertRaises(ValueError):
                cf.verify_envelope(value)

    def test_repeat_deterministic_and_no_native_import(self):
        one = cf.build_envelope("Zeradia", "B1_B2_EXACT", cf.SEEDS[2])
        two = cf.build_envelope("Zeradia", "B1_B2_EXACT", cf.SEEDS[2])
        self.assertEqual(one, two)
        self.assertNotIn("v13.runtime", cf.__dict__)
        self.assertFalse(one["model_output_used"])
        self.assertFalse(one["native_executed"])


if __name__ == "__main__":
    unittest.main()
