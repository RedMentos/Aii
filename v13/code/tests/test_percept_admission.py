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
