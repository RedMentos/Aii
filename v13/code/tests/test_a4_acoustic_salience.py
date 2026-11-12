"""Focused A4 acoustic integration tests; synthetic host-only."""
import math
import unittest
from v13.a4_acoustic_salience import acoustic_salience

class A4SalienceTests(unittest.TestCase):
    def test_silence_and_energy(self):
        quiet = acoustic_salience(0.0, 0.0, duration_ms=20)
        loud = acoustic_salience(0.8, 0.1, duration_ms=20)
        self.assertEqual(quiet["score"], 0.0)
        self.assertGreater(loud["score"], quiet["score"])
        self.assertLessEqual(loud["score"], 1.0)
        self.assertEqual(loud["authority"], "observation_only")
        self.assertIn("speech_probability", loud["unmeasured"])

    def test_bad_inputs(self):
        for rms, zcr, duration in [(float("nan"), 0, 20), (0, float("inf"), 20),
                                   (-0.1, 0, 20), (0, 1.1, 20), (0, 0, 0),
                                   (0, 0, True)]:
            with self.assertRaises(ValueError):
                acoustic_salience(rms, zcr, duration_ms=duration)

    def test_deterministic_bounded(self):
        for x in (0.0, 0.1, 0.5, 1.0):
            a = acoustic_salience(x, 1-x, duration_ms=40)
            self.assertEqual(a, acoustic_salience(x, 1-x, duration_ms=40))
            self.assertTrue(math.isfinite(a["score"]))
            self.assertGreaterEqual(a["score"], 0)
            self.assertLessEqual(a["score"], 1)

if __name__ == "__main__":
    unittest.main()
