"""Fail-closed tokenizer admission regressions (synthetic; not Android proof)."""
import unittest
from v13.prompt_admission import Segment, PromptAdmissionError, admit

class PromptCountIntegrity(unittest.TestCase):
    def test_nonempty_segment_cannot_claim_zero_tokens(self):
        with self.assertRaises(ValueError):
            Segment("USER_EXACT", "2+2", "SOURCE", essential=True, token_count=0)

    def test_empty_segment_may_have_zero_tokens(self):
        self.assertEqual(Segment("STREAM_A", "", "SOURCE", token_count=0).token_count, 0)

    def test_mandatory_source_never_truncated(self):
        with self.assertRaises(PromptAdmissionError):
            admit([Segment("USER_EXACT", "2+2", "SOURCE", essential=True, token_count=90)],
                  context_tokens=100, output_tokens=20, prompt_cap_tokens=90, framing_reserve=4)

    def test_body_offers_are_distinct_when_budget_allows(self):
        segs = [
            Segment("SYSTEM", "rules", "CONTROL", essential=True, token_count=10),
            Segment("USER_EXACT", "question", "SOURCE", essential=True, token_count=10),
            Segment("B1_DETAIL", "detail", "HYPOTHESIS", token_count=10),
            Segment("B2_GIST", "gist", "HYPOTHESIS", token_count=10),
        ]
        result = admit(segs, context_tokens=100, output_tokens=20,
                       prompt_cap_tokens=80, framing_reserve=10)
        self.assertEqual(result.status, "ADMITTED")
        self.assertEqual([s.role for s in result.accepted],
                         ["SYSTEM", "USER_EXACT", "B1_DETAIL", "B2_GIST"])

if __name__ == "__main__":
    unittest.main()
