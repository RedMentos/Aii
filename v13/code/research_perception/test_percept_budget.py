import unittest
from percept_budget import Evidence, admit, estimate_tokens

class AdmissionTests(unittest.TestCase):
    def test_exact_user_never_clipped(self):
        x = admit("x"*500, [], 20)
        self.assertEqual(x.status, "USER_EXCEEDS_BUDGET")
        self.assertIn("x"*500, x.text)
    def test_consent_and_final(self):
        x = admit("hi", [Evidence("a","A5","secret",consented=False),Evidence("b","EAR","provisional",consented=True,final=False)])
        self.assertNotIn("secret",x.text)
        self.assertNotIn("provisional",x.text)
        self.assertEqual(set(x.excluded), {"a","b"})
    def test_provenance_and_priority(self):
        x = admit("hi",[Evidence("low","B2","L"*100,1,True),Evidence("high","A5","H"*100,10,True)],60)
        self.assertEqual(x.included,("high",))
        self.assertEqual(x.excluded,("low",))
        self.assertIn("source=high",x.text)
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            admit("hi",[Evidence("x","A","a"),Evidence("x","B","b")])
    def test_unicode_budget(self):
        x=admit("🙂"*100,[],20)
        self.assertEqual(x.status,"USER_EXCEEDS_BUDGET")
        self.assertGreater(estimate_tokens("🙂"*100),20)
    def test_no_evidence(self):
        self.assertEqual(admit("hi",[]).status,"ADMITTED")
if __name__ == "__main__": unittest.main()
