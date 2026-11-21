"""Offline synthetic regression; no Redmi/native benchmark claim."""
import unittest
from v13.a5_prefill_admission import SourceEnvelope, admit_sources


class AdmissionTests(unittest.TestCase):
    def test_mandatory_preserved_over_optional(self):
        a = admit_sources([SourceEnvelope("B1", "old", 90),
                           SourceEnvelope("USER", "now", 25, required=True)],
                          40, 5)
        self.assertEqual([x.source_id for x in a.accepted], ["now"])
        self.assertEqual(a.status, "PARTIAL_SOURCE_DEFERRED")

    def test_mandatory_overflow_rejects_entire_route(self):
        a = admit_sources([SourceEnvelope("USER", "now", 80, required=True)], 60)
        self.assertEqual(a.status, "REQUIRED_OVER_BUDGET")
        self.assertFalse(a.accepted)

    def test_consent_is_not_bypassed(self):
        a = admit_sources([SourceEnvelope("AUDIO", "private", 2, required=True,
                                           consented=False)], 100)
        self.assertEqual(len(a.rejected), 1)
        self.assertEqual(a.used_tokens, 0)

    def test_no_duplicate_provenance(self):
        with self.assertRaises(ValueError):
            admit_sources([SourceEnvelope("A", "x", 1),
                           SourceEnvelope("B", "x", 1)], 100)

    def test_reservation_and_no_truncation(self):
        a = admit_sources([SourceEnvelope("A5", "one", 15),
                           SourceEnvelope("A5", "two", 12)], 30, 5)
        self.assertEqual([x.source_id for x in a.accepted], ["one"])
        self.assertEqual(a.used_tokens, 15)

    def test_negative_budget(self):
        with self.assertRaises(ValueError):
            admit_sources([], -1)


if __name__ == "__main__":
    unittest.main()
