"""Adversarial software-only checks for Run100 exact B2 quote span candidate."""
import copy
from pathlib import Path
import tempfile
import unittest

from scripts.b2_prior_quote_span_candidate import (
    QuoteBindingRefused, bind_exact_quotes, SCHEMA,
)
from v13.config import initialize
from v13.store import Store


class PriorQuoteSpanCandidate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        initialize(self.home)
        self.store = Store(self.home)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def source(self, text, role="prior"):
        return {"source_role": role, "source_ref": self.store.source(text), "text": text}

    def test_prior_quotes_bind_to_exact_subspans_and_store_revalidates(self):
        prior = self.source("Project Quartz policy. Maximum budget: 230 credits. "
                            "Maximum deadline: 18 ticks. Required local-only: true.")
        current = self.source("Option A costs 200 credits.", "current")
        original = copy.deepcopy(prior)
        quotes = ["Maximum budget: 230 credits.", "Maximum deadline: 18 ticks."]
        out = bind_exact_quotes([prior, current], quotes)
        self.assertEqual(out["schema"], SCHEMA)
        self.assertEqual(out["delivery_authority"], 0)
        self.assertFalse(out["native_utility_proven"])
        self.assertFalse(out["registered_scorer_changed"])
        self.assertEqual([b["source_role"] for b in out["bindings"]], ["prior", "prior"])
        self.assertEqual([self.store.read_source(ref) for ref in out["evidence_refs"]], quotes)
        self.assertEqual(prior, original)
        self.assertEqual({ref["sha256"] for ref in out["evidence_refs"]},
                         {prior["source_ref"]["sha256"]})
        self.assertTrue(all(ref["char_end"] - ref["char_start"] < len(prior["text"])
                            for ref in out["evidence_refs"]))

    def test_current_and_prior_ambiguity_refuses(self):
        a = self.source("The same exact quote.")
        b = self.source("Another source: The same exact quote.", "current")
        with self.assertRaisesRegex(QuoteBindingRefused, "AMBIGUOUS"):
            bind_exact_quotes([a, b], ["The same exact quote."])

    def test_repeated_quote_within_one_source_refuses(self):
        a = self.source("Repeat this. Repeat this.")
        with self.assertRaisesRegex(QuoteBindingRefused, "AMBIGUOUS"):
            bind_exact_quotes([a], ["Repeat this."])

    def test_tampered_hash_and_partial_source_ref_refuse(self):
        a = self.source("A real earlier source.")
        a["source_ref"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(QuoteBindingRefused, "HASH"):
            bind_exact_quotes([a], ["earlier"])
        b = self.source("Another source.")
        b["source_ref"]["char_end"] -= 1
        with self.assertRaisesRegex(QuoteBindingRefused, "FULL_SOURCE"):
            bind_exact_quotes([b], ["source"])

    def test_absent_or_normalized_quote_refuses(self):
        a = self.source("Maximum budget: 230 credits.")
        for quote in ("maximum budget: 230 credits.", "Maximum budget: 230 credits!",
                      "Unknown", " Maximum budget: 230 credits."):
            with self.subTest(quote=quote):
                with self.assertRaisesRegex(QuoteBindingRefused, "QUOTE_NOT_EXACT"):
                    bind_exact_quotes([a], [quote])

    def test_quote_count_duplicate_and_empty_refuse(self):
        a = self.source("Alpha. Beta. Gamma.")
        for quotes in ([], ["Alpha.", "Beta.", "Gamma."], ["Alpha.", "Alpha."]):
            with self.subTest(quotes=quotes):
                with self.assertRaisesRegex(QuoteBindingRefused, "QUOTE_SET"):
                    bind_exact_quotes([a], quotes)

    def test_source_identity_and_role_refuse(self):
        a = self.source("A source.")
        b = dict(a)
        with self.assertRaisesRegex(QuoteBindingRefused, "SOURCE_ID"):
            bind_exact_quotes([a, b], ["source"])
        c = dict(a, source_role="foreign_session")
        with self.assertRaisesRegex(QuoteBindingRefused, "SOURCE_ROLE"):
            bind_exact_quotes([c], ["source"])

    def test_unicode_char_offsets_not_byte_offsets(self):
        a = self.source("🐍 Grüße. Regel: 9 €.")
        out = bind_exact_quotes([a], ["Regel: 9 €."])
        ref = out["evidence_refs"][0]
        self.assertEqual(ref["char_start"], a["text"].index("Regel: 9 €."))
        self.assertEqual(self.store.read_source(ref), "Regel: 9 €.")

    def test_deleted_or_corrupted_store_source_still_refuses(self):
        a = self.source("Original rule: local-only.")
        out = bind_exact_quotes([a], ["local-only."])
        with self.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",
                      (a["source_ref"]["source_id"],))
        with self.assertRaises(ValueError):
            self.store.read_source(out["evidence_refs"][0])


if __name__ == "__main__":
    unittest.main()
