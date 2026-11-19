import unittest
from v13.speech_intent import final_text_intent, verify_intent


class SpeechIntentContract(unittest.TestCase):
    def test_final_text_is_bound_but_cannot_execute(self):
        p = final_text_intent(17, "Hello world", "FINAL", enabled=True)
        self.assertEqual(p["source_message_id"], 17)
        self.assertEqual(p["execution"], "OFF")
        self.assertEqual(p["consent"], "NOT_GRANTED")
        self.assertTrue(verify_intent(p, 17, "Hello world"))
        self.assertFalse(verify_intent(p, 17, "Hello world!"))
        self.assertFalse(verify_intent(p, 18, "Hello world"))

    def test_never_promote_partial_or_failed_text(self):
        for status in ("ERROR", "DEADLINE", "CANCELLED", "INTERRUPTED", "STREAMING"):
            self.assertIsNone(final_text_intent(17, "partial", status, enabled=True))
        self.assertIsNone(final_text_intent(17, "complete", "FINAL"))
        self.assertIsNone(final_text_intent(17, "", "FINAL", enabled=True))

    def test_bounded_input_and_types(self):
        with self.assertRaises(ValueError):
            final_text_intent(True, "text", "FINAL", enabled=True)
        with self.assertRaises(ValueError):
            final_text_intent(1, "x" * 8193, "FINAL", enabled=True)
        with self.assertRaises(ValueError):
            final_text_intent(1, "x\0", "FINAL", enabled=True)


if __name__ == "__main__":
    unittest.main()
