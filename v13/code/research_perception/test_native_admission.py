import unittest
from percept_budget import admit, Evidence
from native_admission import check_native

class NativeAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.a = admit("hello", [Evidence("b1","B1","source",consented=True)],240)
    def test_valid(self):
        x=check_native(self.a, lambda text:20, 64, 16)
        self.assertEqual(x.status,"NATIVE_ADMITTED")
        self.assertIn("USER_EXACT",x.text)
    def test_context_overflow(self):
        self.assertEqual(check_native(self.a,lambda _:50,64,16).status,"NATIVE_CONTEXT_EXCEEDED")
    def test_missing_tokenizer(self):
        def broken(_): raise RuntimeError("offline")
        self.assertEqual(check_native(self.a,broken,64).status,"TOKENIZER_UNAVAILABLE")
    def test_invalid_tokenizer(self):
        for val in (-1,True,2.5,None):
            self.assertEqual(check_native(self.a,lambda _:val,64).status,"INVALID_TOKEN_COUNT")
    def test_user_over_budget_not_sent(self):
        a=admit("x"*500,[],20)
        self.assertIsNone(check_native(a,lambda _:1,64).text)
    def test_output_reservation(self):
        with self.assertRaises(ValueError): check_native(self.a,lambda _:1,32,32)
    def test_exclusions_preserved(self):
        a=admit("hi",[Evidence("no","A5","secret",consented=False)])
        x=check_native(a,lambda _:5,32)
        self.assertEqual(x.excluded,("no",))
        self.assertNotIn("secret",x.text)
if __name__=="__main__": unittest.main()
