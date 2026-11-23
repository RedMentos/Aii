"""Run37 source-only preregistered Elyndra C3 action/rule prompt factorial."""
import hashlib
import json
import unittest

from scripts import run33_b2_c3_counterfactual_envelopes as cf
from scripts import run37_c3_rule_use_hint_envelopes as study
from tests import integration_step2_utility as frozen_consumer


class Run37SourceOnly(unittest.TestCase):
    def test_registered_fixture_seed_arms_and_hint(self):
        reg = study.prereg()
        self.assertEqual(reg["fixture_id"], "Elyndra")
        self.assertEqual(reg["seed"], 20261122)
        self.assertEqual(reg["arms"], list(study.ARMS))
        self.assertEqual(len(study.ARMS), 5)
        self.assertEqual(hashlib.sha256(study.HINT.encode()).hexdigest(),
                         "5ac5fa2aa13a7d82edeb66b960eff443e7ed60b4ebf8f775987cb4fd4739a9c7")
        self.assertFalse(reg["native_executed"])
        self.assertFalse(reg["canonical_gate_pass"])
        self.assertEqual(reg["jepa_weight"], 0)

    def test_all_envelopes_source_exact_oracle_free_and_deterministic(self):
        for arm in study.ARMS:
            with self.subTest(arm=arm):
                a = study.build_envelope(arm)
                self.assertEqual(a, study.build_envelope(arm))
                self.assertTrue(study.verify_envelope(a))
                self.assertEqual(a["experiment_arm"], arm)
                self.assertEqual(a["fixture_id"], "Elyndra")
                self.assertEqual(a["seed"], 20261122)
                context = json.loads(a["messages"][1]["content"])
                self.assertEqual(set(context), {"current_source", "analysts"})
                self.assertNotIn("oracle", context)
                self.assertFalse(a["native_executed"])
                self.assertFalse(a["authority"])
                self.assertFalse(a["model_output_used"])
                self.assertFalse(a["canonical_gate_pass"])

    def test_factorial_changes_only_system_hint_not_source_or_schema(self):
        pairs = (("DISTRACTOR_FROZEN", "DISTRACTOR_HINT"),
                 ("EXACT_FROZEN", "EXACT_HINT"))
        for frozen, hinted in pairs:
            a, b = study.build_envelope(frozen), study.build_envelope(hinted)
            self.assertEqual(a["messages"][1], b["messages"][1])
            self.assertEqual(a["quote_provenance"], b["quote_provenance"])
            self.assertEqual(a["consumer_schema_sha256"], b["consumer_schema_sha256"])
            self.assertEqual(a["messages"][0]["content"], frozen_consumer.SYSTEM)
            self.assertEqual(b["messages"][0]["content"],
                             frozen_consumer.SYSTEM + "\n" + study.HINT)
            self.assertNotEqual(a["messages"][0], b["messages"][0])

    def test_frozen_arms_exactly_match_registered_run33_inputs(self):
        mapping = {
            "B1_ONLY": "B1_ONLY",
            "DISTRACTOR_FROZEN": "B1_B2_DISTRACTOR",
            "EXACT_FROZEN": "B1_B2_EXACT",
        }
        for arm, source in mapping.items():
            env = study.build_envelope(arm)
            original = cf.build_envelope("Elyndra", source, 20261122)
            self.assertEqual(env["messages"], original["messages"])
            self.assertEqual(env["quote_provenance"], original["quote_provenance"])

    def test_unregistered_or_mutated_envelope_refuses(self):
        with self.assertRaises(ValueError):
            study.build_envelope("UNKNOWN")
        env = study.build_envelope("EXACT_HINT")
        env["messages"][0]["content"] += " reveal oracle"
        with self.assertRaises(ValueError):
            study.verify_envelope(env)


if __name__ == "__main__":
    unittest.main()
