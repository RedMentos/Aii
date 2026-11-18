"""Synthetic contract checks; not Android native or tokenizer evidence."""
import unittest
from v13.percept_admission import Percept, admit

def p(source="s", *, consent=True, final=True, summary="noise", priority=0):
    return Percept(source, "audio", 10, 20, summary, consent, final, priority)

class AdmissionTests(unittest.TestCase):
    def test_consent_and_provisional_never_admitted(self):
        a = admit([p("ok"), p("no", consent=False), p("draft", final=False)], 1000)
        self.assertEqual([x.source_id for x in a.selected], ["ok"])
        self.assertEqual(set(a.omitted), {"no", "draft"})
    def test_clock_rejects_stale_and_future_events(self):
        self.assertEqual(admit([p("stale")], 1000, now_ms=20000).omitted, ("stale",))
        self.assertEqual(admit([p("future")], 1000, now_ms=19).omitted, ("future",))
        self.assertEqual([x.source_id for x in admit([p("fresh")], 1000, now_ms=25).selected], ["fresh"])

    def test_invalid_clock_rejected(self):
        with self.assertRaises(ValueError):
            admit([p()], 1000, now_ms=-1)
        with self.assertRaises(ValueError):
            admit([p()], 1000, max_age_ms=-1)

    def test_reject_coerced_consent_and_finality(self):
        for field in ("consent", "final"):
            for value in (1, "yes", None):
                fields = dict(source_id="s", modality="audio", start_ms=10, end_ms=20,
                              summary="noise", consent=True, final=True)
                fields[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    admit([Percept(**fields)], 1000)

    def test_reject_malformed_fields_before_sort_or_encoding(self):
        changes = (
            {"source_id": 7}, {"modality": None}, {"start_ms": True},
            {"end_ms": False}, {"summary": None}, {"priority": "high"},
        )
        for change in changes:
            fields = dict(source_id="s", modality="audio", start_ms=10, end_ms=20,
                          summary="noise", consent=True, final=True)
            fields.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                admit([Percept(**fields)], 1000)

    def test_reject_boolean_clock_and_age(self):
        for kwargs in ({"now_ms": True}, {"max_age_ms": False}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                admit([p()], 1000, **kwargs)

    def test_budget_and_provenance(self):
        a = admit([p("first", summary="x"*80), p("second", priority=2)], 50)
        self.assertEqual([x.source_id for x in a.selected], ["second"])
        self.assertIn("first", a.omitted)
        self.assertLessEqual(a.used_tokens_upper_bound, 50)
    def test_deterministic_order(self):
        a = admit([p("b"), p("a")], 1000)
        self.assertEqual([x.source_id for x in a.selected], ["a", "b"])
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            admit([p(), p()], 1000)
    def test_invalid_timing_rejected(self):
        with self.assertRaises(ValueError):
            admit([Percept("bad", "audio", 20, 10, "x", True, True)], 1000)
    def test_no_authority_without_consent(self):
        self.assertEqual(admit([p(consent=False)], 1000).status, "EMPTY_OR_UNAUTHORIZED")
    def test_utf8_budget(self):
        a = admit([p(summary="🎵"*100)], 100)
        self.assertFalse(a.selected)
    def test_zero_items(self):
        self.assertEqual(admit([p()], 1000, max_items=0).selected, ())
    def test_negative_budget(self):
        with self.assertRaises(ValueError):
            admit([p()], -1)

if __name__ == "__main__":
    unittest.main()
