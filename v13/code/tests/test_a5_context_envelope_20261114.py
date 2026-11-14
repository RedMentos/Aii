import unittest
from v13.a5_context_envelope import A5Item, admit_a5

class AdmissionTests(unittest.TestCase):
    def test_current_source_exact_over_budget(self):
        s = "A" * 900
        out = admit_a5(s, [A5Item("a", "hi", True, True)], budget_chars=0)
        self.assertEqual(out.current_source, s)
        self.assertEqual(out.omitted_ids, ("a",))
    def test_priority_and_omission(self):
        out = admit_a5("hello", [A5Item("low","123456",True,True,0), A5Item("high","x",True,True,9)], budget_chars=8)
        self.assertEqual(out.included_ids, ("high",))
        self.assertIn("low", out.omitted_ids)
    def test_consent_and_finality(self):
        out = admit_a5("x", [A5Item("a","secret",False,True), A5Item("b","draft",True,False)])
        self.assertEqual(out.optional_context, "")
        self.assertEqual(set(out.omitted_ids), {"a","b"})
    def test_reject_truthy_string_consent(self):
        with self.assertRaises(ValueError): admit_a5("x", [A5Item("a","x","false",True)])
    def test_reject_duplicate_source(self):
        with self.assertRaises(ValueError): admit_a5("x", [A5Item("a","1",True,True), A5Item("a","2",True,True)])
    def test_reject_bool_budget(self):
        with self.assertRaises(ValueError): admit_a5("x", [], budget_chars=True)
    def test_reject_multiline_id(self):
        with self.assertRaises(ValueError): admit_a5("x", [A5Item("a\\nb","x",True,True)])
    def test_zero_budget_empty(self):
        out = admit_a5("source", [], budget_chars=0)
        self.assertEqual(out.included_ids, ())
        self.assertEqual(out.omitted_ids, ())

if __name__ == "__main__":
    unittest.main()
