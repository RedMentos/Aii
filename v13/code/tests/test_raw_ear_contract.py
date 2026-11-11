"""Synthetic RAW EAR contract checks; no Android microphone measurement."""
import math
import unittest
from dataclasses import replace
from v13.raw_ear_contract import AcousticFrame, build_raw_ear, encode_record

PCM = bytes(32000)  # exactly 1 s at 16 kHz, synthetic silence
FRAME = AcousticFrame(0, 1000, 0.0, None, 0.0, 1.0)

class RawEarContractTest(unittest.TestCase):
    def make(self, **kw):
        return build_raw_ear("source:test:1", PCM, 16000, (FRAME,), **kw)

    def test_acoustics_survive_without_asr(self):
        packet = self.make()
        record = packet.to_record()
        self.assertEqual(record["modality"], "audio_acoustic")
        self.assertIsNone(record["asr"])
        self.assertEqual(record["frames"][0]["non_speech_probability"], 1.0)
        self.assertFalse(record["android_capture_verified"])
        self.assertIn('"provenance":"provisional"', encode_record(packet))

    def test_optional_teacher_bound_transcript(self):
        packet = self.make(provisional=False, asr_text="hello", asr_teacher_id="frozen:test")
        self.assertEqual(packet.to_record()["asr"]["teacher_id"], "frozen:test")
        self.assertEqual(packet.to_record()["provenance"], "final")
        with self.assertRaises(ValueError):
            self.make(asr_text="unbound")

    def test_reject_nan_and_overlap(self):
        with self.assertRaises(ValueError):
            build_raw_ear("s", PCM, 16000,
                (replace(FRAME, rms=math.nan),))
        with self.assertRaises(ValueError):
            build_raw_ear("s", PCM, 16000,
                (AcousticFrame(0, 600, 0.1, 100, 0.5, 0.1),
                 AcousticFrame(500, 1000, 0.1, 100, 0.5, 0.1)))

    def test_reject_bad_duration_and_pcm(self):
        with self.assertRaises(ValueError):
            build_raw_ear("s", b"x", 16000, (FRAME,))
        with self.assertRaises(ValueError):
            build_raw_ear("s", PCM, 44100, (FRAME,))

if __name__ == "__main__":
    unittest.main()
