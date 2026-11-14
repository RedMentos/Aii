"""Adversarial synthetic RAW EAR boundaries; no live microphone/Redmi evidence."""
import struct
import unittest
from v13.audio_pcm_adapter import pcm16_to_a5

BASE = dict(sample_rate=8000, start_ms=0, event_id="synthetic-e",
            generation_id="synthetic-g", source_id="synthetic-source",
            source_sha256="b"*64, consent_receipt="synthetic-consent")

class AudioBoundaryTests(unittest.TestCase):
    def test_exact_minimum_one_millisecond(self):
        p = pcm16_to_a5(pcm=struct.pack("<h", 1000)*8, **BASE)
        self.assertEqual(p["segments"][0]["end_ms"], 1)
        self.assertEqual(p["segments"][0]["finality"], "PROVISIONAL")

    def test_finality_preserved_without_asr(self):
        p = pcm16_to_a5(pcm=b"\x00\x00"*80, **(BASE | {"finality":"FINAL"}))
        s = p["segments"][0]
        self.assertEqual(s["finality"], "FINAL")
        self.assertIsNone(s["asr_transcript"])
        self.assertFalse(s["action_authority"])

    def test_no_consent_with_whitespace_receipt(self):
        with self.assertRaises(PermissionError):
            pcm16_to_a5(pcm=b"\x00\x00"*80, **(BASE | {"consent_receipt":"  "}))

    def test_reject_nonfinite_and_wrong_timestamp_types(self):
        for t in (True, 1.5, -1, float("nan")):
            with self.subTest(t=t), self.assertRaises(ValueError):
                pcm16_to_a5(pcm=b"\x00\x00"*80, **(BASE | {"start_ms":t}))

    def test_source_hash_not_inferred_from_pcm(self):
        with self.assertRaises(ValueError):
            pcm16_to_a5(pcm=b"\x00\x00"*80, **(BASE | {"source_sha256":"unverified"}))

    def test_oversized_192khz_frame_rejected(self):
        with self.assertRaises(ValueError):
            pcm16_to_a5(pcm=b"\x00\x00"*192001,
                        **(BASE | {"sample_rate":192000}))

if __name__ == "__main__":
    unittest.main()
