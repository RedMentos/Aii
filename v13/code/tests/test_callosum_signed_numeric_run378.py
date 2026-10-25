"""Run378 RED-first: signed numerical evidence cannot be mistaken for agreement."""
import unittest

from v13 import callosum as C


REF = {"source_id": "source", "sha256": "0" * 64, "char_start": 0, "char_end": 2, "modality": "text"}


def offer(role, summary, evidence=True):
    return {
        "role": role, "offer": {"summary": summary, "quotes": [], "needs_reentry": False},
        "evidence_refs": [REF] if evidence else [],
    }


class SignedNumericEvidenceRun378(unittest.TestCase):
    def test_negative_vs_positive_or_unsigned_is_contradiction_with_evidence(self):
        for receiver in ("Change is 4", "Change is +4", "Change is +4.0"):
            sender = "Change is -4.0" if receiver.endswith(".0") else "Change is -4"
            with self.subTest(sender=sender, receiver=receiver):
                gain, why = C.signed_gain(offer("B1_DETAIL", sender), offer("B2_GIST", receiver))
                self.assertEqual((gain, why), (-0.5, "EXACT_EVIDENCE_CONTRADICTS_RECEIVER"))

    def test_matching_signs_and_explicit_plus_agree(self):
        for a, b in (("-4", "-4"), ("+4", "4"), ("-4.0", "-4.0"), ("+4.0", "4.0")):
            with self.subTest(a=a, b=b):
                gain, why = C.signed_gain(offer("B1_DETAIL", "Delta " + a),
                                          offer("B2_GIST", "Delta " + b))
                self.assertEqual((gain, why), (0.5, "AGREES_WITH_RECEIVER"))

    def test_no_source_evidence_never_authorizes_suppression(self):
        gain, why = C.signed_gain(offer("B1_DETAIL", "Delta -4", evidence=False),
                                  offer("B2_GIST", "Delta +4"))
        self.assertEqual((gain, why), (0.0, "NEUTRAL"))

    def test_hyphenated_range_is_not_negative_four(self):
        self.assertEqual(C.nums("Range 3-4"), {"3", "4"})
        self.assertIn("-4", C.nums("Delta -4"))
        self.assertIn("4", C.nums("Delta +4"))
        self.assertNotIn("-4", C.nums("Delta +4"))


if __name__ == "__main__":
    unittest.main()
