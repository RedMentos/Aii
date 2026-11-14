"""Consent/finality type boundary: synthetic A-plane admission regression."""
import unittest
from v13.percept_admission import Percept, admit


class ConsentFinalTypes(unittest.TestCase):
    def packet(self, **changes):
        args = dict(source_id="synthetic-1", modality="audio", start_ms=0,
                    end_ms=20, summary="synthetic acoustic event",
                    consent=True, final=True)
        args.update(changes)
        return Percept(**args)

    def test_string_consent_rejected(self):
        with self.assertRaises(ValueError):
            admit([self.packet(consent="false")], 200)

    def test_numeric_consent_rejected(self):
        with self.assertRaises(ValueError):
            admit([self.packet(consent=1)], 200)

    def test_string_final_rejected(self):
        with self.assertRaises(ValueError):
            admit([self.packet(final="false")], 200)

    def test_numeric_final_rejected(self):
        with self.assertRaises(ValueError):
            admit([self.packet(final=1)], 200)

    def test_explicit_false_consent_omitted(self):
        result = admit([self.packet(consent=False)], 200)
        self.assertEqual(result.selected, ())
        self.assertEqual(result.omitted, ("synthetic-1",))

    def test_explicit_false_final_omitted(self):
        result = admit([self.packet(final=False)], 200)
        self.assertEqual(result.selected, ())
        self.assertEqual(result.omitted, ("synthetic-1",))

    def test_explicit_true_admitted(self):
        result = admit([self.packet()], 200)
        self.assertEqual(len(result.selected), 1)


if __name__ == "__main__":
    unittest.main()
