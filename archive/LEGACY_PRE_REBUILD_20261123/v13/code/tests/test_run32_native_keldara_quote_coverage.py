"""Synthetic-only Run32 native quote delivery audit tests (no native inference)."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import run15_step2_disjoint_bilingual_fixtures as fresh
from scripts import run30_native_keldara_aggregate_audit as sealed
from scripts import run32_native_keldara_quote_coverage as audit


class QuoteCoverageAuditTests(unittest.TestCase):
    def setUp(self):
        self.fixture = next(f for f in fresh.FIXTURES if f["id"] == "Keldara")
        self.report = {
            "fixture_sha256": sealed.FIXTURE_SHA256,
            "fixtures": [self.fixture],
            "rows": [],
        }
        for variant in sealed.VARIANTS:
            analysts = []
            for role in audit.EXPECTED_ROLES[variant]:
                quotes = ([self.fixture["history"][2]]
                          if role == "B1_DETAIL" else
                          [] if variant == "both_exact" else
                          [self.fixture["history"][0]])
                analysts.append({"role": role, "verified_quotes": quotes})
            self.report["rows"].append({
                "fixture": "Keldara", "variant": variant,
                "consumer_messages": [
                    {"role": "system", "content": "synthetic-only"},
                    {"role": "user", "content": json.dumps({
                        "current_source": self.fixture["current"],
                        "analysts": analysts,
                    })},
                ],
            })

    def test_clean_synthetic_detects_b2_rule_quote_gap(self):
        result = audit.summarize_report(self.report)
        self.assertEqual(result["both_exact_b2_verified_quotes"], 0)
        self.assertIs(result["both_exact_b2_rules_present"], False)
        self.assertIs(result["both_exact_b1_options_present"], True)
        self.assertIs(result["role_coverage"]["b2_only"]["B2_GIST"]["rules"], True)
        self.assertEqual(result["quote_counts"]["same_policy_dual"]["B1_DETAIL"], 2)
        self.assertFalse(result["canonical_gate_pass"])
        self.assertFalse(result["whole_system_complete"])
        output = json.dumps(result)
        self.assertNotIn(self.fixture["current"], output)
        self.assertNotIn(self.fixture["history"][0], output)

    def test_reject_duplicate_or_missing_variant(self):
        bad = copy.deepcopy(self.report)
        bad["rows"][0]["variant"] = bad["rows"][1]["variant"]
        with self.assertRaises(ValueError):
            audit.summarize_report(bad)
        bad = copy.deepcopy(self.report)
        bad["rows"].pop()
        with self.assertRaises(ValueError):
            audit.summarize_report(bad)

    def test_reject_wrong_role_and_missing_verified_quotes(self):
        bad = copy.deepcopy(self.report)
        user = json.loads(bad["rows"][3]["consumer_messages"][1]["content"])
        user["analysts"][1]["role"] = "C3_LANGUAGE"
        bad["rows"][3]["consumer_messages"][1]["content"] = json.dumps(user)
        with self.assertRaises((ValueError, KeyError)):
            audit.summarize_report(bad)
        bad = copy.deepcopy(self.report)
        user = json.loads(bad["rows"][3]["consumer_messages"][1]["content"])
        user["analysts"][1]["verified_quotes"] = None
        bad["rows"][3]["consumer_messages"][1]["content"] = json.dumps(user)
        with self.assertRaises((ValueError, TypeError)):
            audit.summarize_report(bad)

    def test_reject_wrong_fixture_and_unsealed_zip(self):
        bad = copy.deepcopy(self.report)
        bad["fixture_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            audit.summarize_report(bad)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "unsealed.zip"
            path.write_bytes(b"not-original")
            with self.assertRaises(ValueError):
                audit.audit_zip(path)


if __name__ == "__main__":
    unittest.main()
