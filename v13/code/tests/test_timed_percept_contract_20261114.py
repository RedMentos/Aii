"""Regression for existing A5 timed-percept lineage and consent boundaries."""
import unittest
from dataclasses import replace
from v13.timed_percept import TimedPercept, provisional_to_final

class TimedPerceptContractTest(unittest.TestCase):
    def setUp(self):
        self.p = TimedPercept("audio", "fixture:synthetic", 100, 140, "fixture-consent", rms=0.12, pitch_hz=180.0, non_speech="music")
    def test_nonverbal_without_transcript(self):
        packet = self.p.packet()
        self.assertEqual(packet["non_speech"], "music")
        self.assertIsNone(packet["transcript"])
    def test_teacher_provenance(self):
        with self.assertRaises(ValueError): replace(self.p, transcript="hello")
        self.assertEqual(replace(self.p, transcript="hello", provenance="teacher").packet()["transcript"], "hello")
    def test_consent(self):
        with self.assertRaises(ValueError): replace(self.p, consent_id="")
    def test_time_regression(self):
        with self.assertRaises(ValueError): replace(self.p, end_ms=99)
    def test_nonfinite(self):
        with self.assertRaises(ValueError): replace(self.p, rms=float("nan"))
    def test_probability(self):
        with self.assertRaises(ValueError): replace(self.p, speech_probability=1.1)
    def test_final_lineage(self):
        final = replace(self.p, stage="final", end_ms=160)
        self.assertEqual(provisional_to_final(self.p, final)["stage"], "final")
    def test_cross_consent_final_rejected(self):
        with self.assertRaises(ValueError): provisional_to_final(self.p, replace(self.p, stage="final", consent_id="other"))
    def test_cross_source_final_rejected(self):
        with self.assertRaises(ValueError): provisional_to_final(self.p, replace(self.p, stage="final", source="other"))
    def test_ui_no_audio_leak(self):
        with self.assertRaises(ValueError): TimedPercept("android_ui", "fixture:ui", 1, 2, "fixture-consent", rms=0.1)

if __name__ == "__main__":
    unittest.main()
