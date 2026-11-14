import unittest
from dataclasses import replace
from v13.timed_percept import TimedPercept, provisional_to_final

class TimedPerceptContractTests(unittest.TestCase):
    def setUp(self):
        self.p = TimedPercept("audio", "fixture", 100, 120, "test-consent", rms=.1, speech_probability=.2, non_speech="click")
    def test_nonverbal_without_asr(self):
        p = self.p.packet()
        self.assertEqual(p["non_speech"], "click")
        self.assertIsNone(p["transcript"])
        self.assertEqual(p["authority"], "observation_only")
    def test_final(self):
        self.assertEqual(provisional_to_final(self.p, replace(self.p, stage="final", end_ms=130))["end_ms"], 130)
    def test_consent_mismatch(self):
        with self.assertRaises(ValueError):
            provisional_to_final(self.p, replace(self.p, stage="final", consent_id="other"))
    def test_time_regression(self):
        with self.assertRaises(ValueError):
            provisional_to_final(self.p, replace(self.p, stage="final", end_ms=110))
    def test_no_fake_asr(self):
        with self.assertRaises(ValueError):
            replace(self.p, transcript="invented")
    def test_probability_bound(self):
        with self.assertRaises(ValueError):
            replace(self.p, speech_probability=1.1)
    def test_no_audio_on_ui(self):
        with self.assertRaises(ValueError):
            replace(self.p, modality="android_ui")
    def test_no_implicit_consent(self):
        with self.assertRaises(ValueError):
            replace(self.p, consent_id="")

if __name__ == "__main__":
    unittest.main()
