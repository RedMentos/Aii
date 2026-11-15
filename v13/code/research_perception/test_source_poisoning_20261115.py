"""Adversarial SHADOW checks for PR #1972 QA review."""
import unittest
from percept_admission import Percept, admit

class SourcePoisoningTests(unittest.TestCase):
    def p(self, source="s", *, consent=True, final=True, text="source", tokens=1):
        return Percept(source, text, tokens, consent, final, "audio")

    def test_unconsented_then_authorized(self):
        r = admit([self.p(consent=False), self.p()], 2)
        self.assertEqual([p.text for p in r["accepted"]], ["source"])
        self.assertEqual(r["rejected"], (("s", "NO_CONSENT"),))

    def test_authorized_then_unconsented(self):
        r = admit([self.p(), self.p(consent=False)], 2)
        self.assertEqual(len(r["accepted"]), 1)
        self.assertEqual(r["rejected"], (("s", "DUPLICATE_OR_MISSING_SOURCE"),))

    def test_provisional_to_final(self):
        r = admit([self.p(final=False), self.p()], 2)
        self.assertEqual(len(r["accepted"]), 1)
        self.assertEqual(r["rejected"], (("s", "PROVISIONAL"),))

    def test_overbudget_does_not_poison_later_smaller_final(self):
        r = admit([self.p(tokens=4), self.p(tokens=1)], 2)
        self.assertEqual(len(r["accepted"]), 1)
        self.assertEqual(r["rejected"], (("s", "BUDGET_EXCEEDED"),))

    def test_source_id_type_and_bounds(self):
        for source in (None, 42, [], "", "x" * 257):
            with self.subTest(source=repr(source)[:20]):
                self.assertEqual(admit([self.p(source)], 2)["rejected"][0][1], "INVALID_SOURCE")

    def test_payload_type_and_bounds(self):
        for value in (None, 42, "x" * 65537):
            with self.subTest(value=type(value).__name__):
                self.assertEqual(admit([self.p(text=value)], 2)["rejected"][0][1], "INVALID_TEXT")

    def test_bool_estimate_and_flags(self):
        self.assertEqual(admit([self.p(tokens=True)], 2)["rejected"][0][1], "INVALID_ESTIMATE")
        self.assertEqual(admit([self.p(consent=1)], 2)["rejected"][0][1], "NO_CONSENT")
        self.assertEqual(admit([self.p(final=1)], 2)["rejected"][0][1], "PROVISIONAL")

if __name__ == "__main__":
    unittest.main()
