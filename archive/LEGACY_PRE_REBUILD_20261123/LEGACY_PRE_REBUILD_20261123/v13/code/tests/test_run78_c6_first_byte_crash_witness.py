"""Real temporary SQLite, synthetic no-stream C6 first-byte lifecycle witness."""
import unittest

from scripts.run78_c6_first_byte_crash_witness import witness


class C6FirstByteCrashWitnessTests(unittest.TestCase):
    def test_commit_without_stream_cannot_prove_visible_byte(self):
        r = witness()
        self.assertEqual(r["status"], "ZERO_BYTE_COMMIT_WINDOW_REPRODUCED")
        self.assertTrue(r["commit_output_returned"])
        self.assertEqual(r["status_before_restart"], "OUTPUT_COMMITTED")
        self.assertEqual(r["status_after_restart"], "INTERRUPTED")
        self.assertEqual(r["synthetic_stream_bytes_sent"], 0)
        self.assertTrue(r["stored_candidate_retained"])
        self.assertTrue(r["closed_store_ok"])
        self.assertFalse(r["native_model_called"])
        self.assertFalse(r["real_tty_approved"])
        self.assertEqual(r["production_authority"], 0)


if __name__ == "__main__":
    unittest.main()
