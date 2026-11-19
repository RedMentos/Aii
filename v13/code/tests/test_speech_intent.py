import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from v13.runtime import Runtime
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

    def test_runtime_sqlite_final_and_restart(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            runtime = Runtime(home)
            try:
                session = runtime.session
                mid = runtime.store.message(session, None, "assistant",
                                            "A final answer", "FINAL")
                partial = runtime.store.message(session, None, "assistant",
                                                "unfinished", "DEADLINE")
                intent = runtime.speech_intent(mid)
                self.assertTrue(verify_intent(intent, mid, "A final answer"))
                self.assertEqual(intent["execution"], "OFF")
                self.assertIsNone(runtime.speech_intent(partial))
                with self.assertRaises(ValueError):
                    runtime.speech_intent(True)
            finally:
                runtime.close()
            restarted = Runtime(home)
            try:
                self.assertTrue(verify_intent(
                    restarted.speech_intent(mid), mid, "A final answer"))
                self.assertIsNone(restarted.speech_intent(partial))
            finally:
                restarted.close()

    def test_bounded_input_and_types(self):
        with self.assertRaises(ValueError):
            final_text_intent(True, "text", "FINAL", enabled=True)
        with self.assertRaises(ValueError):
            final_text_intent(1, "x" * 8193, "FINAL", enabled=True)
        with self.assertRaises(ValueError):
            final_text_intent(1, "x\0", "FINAL", enabled=True)


if __name__ == "__main__":
    unittest.main()
