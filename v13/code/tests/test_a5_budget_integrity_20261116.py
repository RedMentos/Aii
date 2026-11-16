"""Regression for real prefill token accounting; synthetic only, no Redmi claim."""
import math
import unittest

from v13.a5_prefill_admission import SourceEnvelope, admit_sources


class TestA5BudgetIntegrity(unittest.TestCase):
    def test_invalid_source_token_counts(self):
        for value in (float("nan"), float("inf"), -1, 1.5, True, "10", None):
            with self.subTest(value=repr(value)), self.assertRaises((ValueError, TypeError)):
                SourceEnvelope("A_PERCEPTION", "source-1", value)

    def test_invalid_global_budget(self):
        source = [SourceEnvelope("A_PERCEPTION", "source-1", 2, required=True)]
        for value in (float("nan"), float("inf"), 2.5, True, "10", None):
            with self.subTest(value=repr(value)), self.assertRaises((ValueError, TypeError)):
                admit_sources(source, value)
                # The route must not silently treat malformed accounting as admitted.

    def test_invalid_reserved_budget(self):
        for value in (float("nan"), float("-inf"), 1.5, False, None):
            with self.subTest(value=repr(value)), self.assertRaises((ValueError, TypeError)):
                admit_sources([], 100, reserved_tokens=value)

    def test_non_boolean_consent_and_required(self):
        with self.assertRaises(ValueError):
            SourceEnvelope("A_PERCEPTION", "source-1", 2, consented="false")
        with self.assertRaises(ValueError):
            SourceEnvelope("A_PERCEPTION", "source-1", 2, required=1)

    def test_unconsented_required_source_cannot_be_admitted(self):
        sources = [SourceEnvelope("AUDIO", "private", 2, required=True, consented=False),
                   SourceEnvelope("USER", "current", 3, required=True)]
        a = admit_sources(sources, 100)
        self.assertEqual(a.status, "REQUIRED_CONSENT_MISSING")
        self.assertEqual(a.accepted, ())
        self.assertEqual(a.used_tokens, 0)
        self.assertEqual(len(a.rejected), 2)

    def test_required_over_budget_does_not_fake_admission(self):
        s = [SourceEnvelope("A_PERCEPTION", "user-source", 11, required=True)]
        a = admit_sources(s, 10)
        self.assertEqual(a.status, "REQUIRED_OVER_BUDGET")
        self.assertEqual(a.accepted, ())
        self.assertEqual(a.used_tokens, 0)

    def test_source_provenance_preserved_on_partial(self):
        s = [SourceEnvelope("STREAM_B", "user-source", 8, required=True),
             SourceEnvelope("B2_GIST", "optional-source", 6)]
        a = admit_sources(s, 10)
        self.assertEqual(a.status, "PARTIAL_SOURCE_DEFERRED")
        self.assertEqual([x.source_id for x in a.accepted], ["user-source"])
        self.assertEqual([x.source_id for x in a.deferred], ["optional-source"])


if __name__ == "__main__":
    unittest.main()
