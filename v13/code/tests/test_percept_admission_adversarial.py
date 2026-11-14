"""Additional adversarial A5 admission regressions (synthetic only)."""
import unittest
from v13.percept_admission import Percept, admit


def item(key, summary="tone", consent=True, final=True, priority=0):
    return Percept(key, "audio", 0, 10, summary, consent, final, priority)


class AdmissionAdversarialTests(unittest.TestCase):
    def test_no_raw_unconsented_evidence(self):
        out = admit([item("private", "sensitive", consent=False), item("public")], 1000)
        self.assertNotIn("private", [x.source_id for x in out.selected])
        self.assertIn("private", out.omitted)

    def test_provisional_never_promoted(self):
        out = admit([item("provisional", final=False)], 1000)
        self.assertFalse(out.selected)

    def test_multibyte_is_bounded(self):
        out = admit([item("unicode", "🎵" * 100)], 100)
        self.assertFalse(out.selected)

    def test_priority_is_deterministic(self):
        out = admit([item("low"), item("high", priority=3)], 1000)
        self.assertEqual([p.source_id for p in out.selected], ["high", "low"])

    def test_exact_budget_boundary(self):
        p = item("a")
        cost = len((p.source_id + p.modality + p.summary).encode("utf-8")) + 32
        self.assertEqual(admit([p], cost).selected, (p,))
        self.assertFalse(admit([p], cost - 1).selected)

    def test_oversized_stream_rejected(self):
        with self.assertRaises(ValueError):
            admit([item(str(i)) for i in range(4097)], 100000)


if __name__ == "__main__":
    unittest.main()
