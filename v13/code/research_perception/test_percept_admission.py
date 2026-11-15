import unittest
from percept_admission import Percept, admit

class AdmissionTests(unittest.TestCase):
    def p(self, key="a", tokens=2, consent=True, final=True, modality="audio"):
        return Percept(key, "source-bound payload", tokens, consent, final, modality)
    def test_exact_boundary(self):
        self.assertEqual(len(admit([self.p()], 2)["accepted"]), 1)
    def test_overflow_no_truncation(self):
        result = admit([self.p(), self.p("b")], 3)
        self.assertEqual(result["rejected"], (("b", "BUDGET_EXCEEDED"),))
        self.assertEqual(result["accepted"][0].text, "source-bound payload")
    def test_consent(self):
        self.assertEqual(admit([self.p(consent=False)], 5)["rejected"][0][1], "NO_CONSENT")
    def test_provisional(self):
        self.assertEqual(admit([self.p(final=False)], 5)["rejected"][0][1], "PROVISIONAL")
    def test_duplicate(self):
        self.assertEqual(admit([self.p(), self.p()], 5)["rejected"][0][1], "DUPLICATE_OR_MISSING_SOURCE")
    def test_modality(self):
        self.assertEqual(admit([self.p(modality="camera")], 5)["rejected"][0][1], "MODALITY_OFF")
    def test_negative_budget(self):
        with self.assertRaises(ValueError): admit([], -1)
    def test_invalid_estimate(self):
        self.assertEqual(admit([self.p(tokens=-1)], 5)["rejected"][0][1], "INVALID_ESTIMATE")
    def test_native_unverified(self):
        self.assertFalse(admit([self.p()], 5)["native_tokenizer_verified"])

if __name__ == "__main__":
    unittest.main()
