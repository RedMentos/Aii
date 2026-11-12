"""Cross-process speech producer capacity regression (synthetic SQLite only)."""
import os
import tempfile
import threading
import unittest

from v13.speech_intent import SpeechIntentError, SpeechIntentQueue


class SpeechProducerCapacityTests(unittest.TestCase):
    def test_two_connections_never_overfill_single_slot(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "speech.sqlite")
            a = SpeechIntentQueue(path, max_pending=1)
            b = SpeechIntentQueue(path, max_pending=1)
            barrier = threading.Barrier(2)
            outcomes = []
            lock = threading.Lock()

            def produce(queue, text):
                barrier.wait()
                try:
                    queue.submit(text, source_id="C3")
                    result = "accepted"
                except SpeechIntentError as exc:
                    result = str(exc)
                with lock:
                    outcomes.append(result)

            t1 = threading.Thread(target=produce, args=(a, "one"))
            t2 = threading.Thread(target=produce, args=(b, "two"))
            t1.start()
            t2.start()
            t1.join(timeout=5)
            t2.join(timeout=5)
            self.assertFalse(t1.is_alive() or t2.is_alive())
            self.assertCountEqual(outcomes, ["accepted", "queue full"])
            self.assertEqual(a.db.execute(
                "SELECT count(*) FROM speech_intents WHERE status='QUEUED'"
            ).fetchone()[0], 1)
            # A full-queue error must not strand an open write transaction.
            self.assertEqual(a.interrupt(), 1)
            b.submit("after stop", source_id="C3")
            a.close()
            b.close()

    def test_failed_submit_rolls_back_transaction(self):
        with tempfile.TemporaryDirectory() as d:
            queue = SpeechIntentQueue(os.path.join(d, "speech.sqlite"), max_pending=1)
            queue.submit("first", source_id="C3")
            with self.assertRaisesRegex(SpeechIntentError, "queue full"):
                queue.submit("second", source_id="C3")
            self.assertFalse(queue.db.in_transaction)
            self.assertEqual(queue.interrupt(), 1)
            self.assertEqual(queue.submit("third", source_id="C3").status, "QUEUED")
            queue.close()


if __name__ == "__main__":
    unittest.main()
