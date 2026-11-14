"""Offline synthetic contract checks; no microphone, GGUF or Android claims."""
import unittest
from dataclasses import replace
from v13.audio_raw_ear_contract import synthetic_pcm_packet

class RawEarContractTests(unittest.TestCase):
    def test_silence_keeps_acoustic_not_asr(self):
        p = synthetic_pcm_packet([0.0]*160, source_id="fixture", start_ms=20)
        self.assertEqual((p.start_ms,p.end_ms), (20,30))
        self.assertEqual((p.rms,p.peak,p.zero_crossing_rate), (0,0,0))
        self.assertIsNone(p.teacher_transcript)
        self.assertIn('"provenance": "synthetic"',p.to_json())

    def test_nonverbal_signal(self):
        p = synthetic_pcm_packet([-0.5,0.5,-0.5,0.5],source_id="nonverbal",start_ms=0)
        self.assertEqual(p.peak,0.5)
        self.assertEqual(p.zero_crossing_rate,1)
        self.assertIsNone(p.speech_probability)

    def test_rejects_unconsented_and_forged_provenance(self):
        p = synthetic_pcm_packet([0.1],source_id="a",start_ms=0)
        for bad in (replace(p,consent_scope="none"),replace(p,provenance="android_verified"),
                    replace(p,phase="done"),replace(p,start_ms=p.end_ms),
                    replace(p,teacher_transcript="hello")):
            with self.assertRaises(ValueError): bad.validate()

    def test_rejects_nan_and_out_of_range(self):
        for samples in ([float("nan")],[2.0],[]):
            with self.assertRaises(ValueError):
                synthetic_pcm_packet(samples,source_id="a",start_ms=0)
        p = synthetic_pcm_packet([0.1],source_id="a",start_ms=0)
        with self.assertRaises(ValueError): replace(p,speech_probability=float("nan")).validate()

if __name__ == "__main__":
    unittest.main()
