"""Run400 RED-first: B2 verified quotes are exact source spans, not whole messages."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run394_step2_fresh as r394
import run396_step2_pilot_audit as audit


def rows(fixture, quotes):
    return {(fixture["id"], v): {
        "consumer_messages": [{"role": "user", "content": json.dumps({
            "analysts": [{"role": "B2_GIST", "verified_quotes": quotes}]})}]
    } for v in audit.B2_VARIANTS}


class Run400QuoteSubstringTests(unittest.TestCase):
    def fixture(self, name):
        return next(f for f in r394.FIXTURES if f["id"] == name)

    def test_exact_truncated_kickoff_quote_is_sourced_not_hallucination(self):
        f = self.fixture("Alder")
        q = f["history"][0][:198]
        self.assertTrue(q in f["history"][0])
        self.assertNotIn(q, f["history"])
        result = audit.quote_provenance(rows(f, [q]), f)
        self.assertEqual(result["historical_exact_rule_quotes"], 0)
        self.assertFalse(result["revision_overrides_historical_rule"])

    def test_exact_internal_historical_rule_span_is_sourced_and_counted(self):
        f = self.fixture("Delta")
        q = f["history"][0][-133:]
        self.assertIn("Local-only requirement: false.", q)
        result = audit.quote_provenance(rows(f, [q]), f)
        self.assertEqual(result["historical_exact_rule_quotes"], 4)
        self.assertTrue(result["revision_overrides_historical_rule"])

    def test_current_revision_substring_is_sourced_not_historical(self):
        f = self.fixture("Delta")
        q = f["current"][:156]
        self.assertIn("Budget 100 euros.", q)
        result = audit.quote_provenance(rows(f, [q]), f)
        self.assertEqual(result["historical_exact_rule_quotes"], 0)

    def test_unsourced_near_match_is_rejected_even_if_rule_matches(self):
        f = self.fixture("Delta")
        q = f["history"][0][-133:] + " UNSOURCED"
        with self.assertRaisesRegex(ValueError, "not exact frozen source"):
            audit.quote_provenance(rows(f, [q]), f)

    def test_case_altered_source_span_is_rejected(self):
        f = self.fixture("Alder")
        q = f["history"][0][:198].replace("kickoff", "Kickoff")
        with self.assertRaisesRegex(ValueError, "not exact frozen source"):
            audit.quote_provenance(rows(f, [q]), f)

    def test_empty_quote_is_rejected_not_substring_of_everything(self):
        f = self.fixture("Alder")
        with self.assertRaisesRegex(ValueError, "not exact frozen source"):
            audit.quote_provenance(rows(f, [""]), f)

    def test_nonstring_quote_is_rejected(self):
        f = self.fixture("Alder")
        for value in (None, 1, False, ["text"], {"q": "text"}):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "non-string"):
                audit.quote_provenance(rows(f, [value]), f)


if __name__ == "__main__":
    unittest.main()
