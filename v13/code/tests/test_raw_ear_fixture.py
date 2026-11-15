"""Offline synthetic tests for A5 RAW EAR fixture and consent/lineage gates."""
import unittest
from v13.raw_ear_fixture import synthetic_pcm_to_percept
from v13.timed_percept import TimedPercept, provisional_to_final

class RawEarFixtureTests(unittest.TestCase):
    def test_rms_packet(self):
        p = synthetic_pcm_to_percept([0.5, -0.5], 8000, 10, "fixture", "consent")
        self.assertAlmostEqual(p.rms, .5)
        self.assertEqual(p.packet()["authority"], "observation_only")
        self.assertEqual(p.packet()["schema"], "v13.a5.timed-percept/1")
        self.assertIsNone(p.transcript)
    def test_no_consent(self):
        with self.assertRaises(PermissionError):
            synthetic_pcm_to_percept([0], 8000, 0, "fixture", "")
    def test_invalid_pcm(self):
        for pcm in ([], [float("nan")], [1.5]):
            with self.subTest(pcm=pcm), self.assertRaises(ValueError):
                synthetic_pcm_to_percept(pcm, 8000, 0, "fixture", "yes")
    def test_final_lineage(self):
        p = synthetic_pcm_to_percept([0], 8000, 0, "fixture", "yes")
        q = synthetic_pcm_to_percept([0, 0], 8000, 0, "fixture", "yes", "final")
        self.assertEqual(provisional_to_final(p, q)["stage"], "final")
        bad = synthetic_pcm_to_percept([0], 8000, 0, "other", "yes", "final")
        with self.assertRaises(ValueError):
            provisional_to_final(p, bad)
    def test_no_teacher_forgery(self):
        with self.assertRaises(ValueError):
            TimedPercept("audio", "fixture", 0, 1, "yes", transcript="fake")

if __name__ == "__main__":
    unittest.main()
