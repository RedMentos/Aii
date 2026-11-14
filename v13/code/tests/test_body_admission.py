import unittest
from v13.body_admission import admit

class BodyAdmissionTests(unittest.TestCase):
    def test_preserves_source_peer_and_jef_while_dropping_optional(self):
        q = {"source_segments": [{"text": "exact source", "source_ref": {"char_start": 0, "char_end": 12}}],
             "peer_message": {"text": "B2 to B1"}, "jef_query": {"question": "why?"},
             "earlier_context": ["x" * 1000], "self_corollary": {"text": "y" * 1000}}
        before = repr(q)
        out, receipt = admit(q, max_optional_chars=50)
        self.assertEqual(repr(q), before)
        self.assertEqual(out["source_segments"], q["source_segments"])
        self.assertEqual(out["peer_message"], q["peer_message"])
        self.assertEqual(out["jef_query"], q["jef_query"])
        self.assertTrue(receipt["removed_optional_fields"])
        self.assertTrue(receipt["current_source_preserved"])
        self.assertTrue(receipt["peer_preserved"])

    def test_short_optional_context_retained(self):
        q = {"source_segments": [{"text": "abc"}], "prior_hypothesis": "x"}
        out, receipt = admit(q, max_optional_chars=100)
        self.assertEqual(out, q)
        self.assertEqual(receipt["removed_optional_fields"], [])

    def test_invalid_cap_refused(self):
        for cap in (-1, 1.2, True):
            with self.assertRaises(ValueError):
                admit({}, max_optional_chars=cap)

if __name__ == "__main__":
    unittest.main()
