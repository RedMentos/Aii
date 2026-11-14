"""Synthetic streaming PCM regression; no Android hardware evidence."""
import math
import struct
import unittest
from v13.audio_pcm_adapter import pcm16_to_a5

ARGS = dict(sample_rate=8000, start_ms=100, event_id="fixture-event",
            generation_id="fixture-generation", source_id="fixture-source",
            source_sha256="a"*64, consent_receipt="synthetic-only")

class StreamingPCMTests(unittest.TestCase):
    def test_constant_positive_full_second(self):
        p = pcm16_to_a5(pcm=struct.pack("<h", 16384)*8000, **ARGS)
        s = p["segments"][0]
        self.assertEqual((s["start_ms"], s["end_ms"]), (100, 1100))
        self.assertAlmostEqual(s["acoustic"]["rms"], 0.5, places=7)
        self.assertEqual(s["acoustic"]["zcr"], 0)
        self.assertFalse(s["learning_authority"])

    def test_alternating_sign_exact_crossings(self):
        p = pcm16_to_a5(pcm=struct.pack("<hhhh", -1, 1, -1, 1)*20, **ARGS)
        self.assertEqual(p["segments"][0]["acoustic"]["zcr"], 1.0)

    def test_negative_fullscale_rms_one(self):
        p = pcm16_to_a5(pcm=struct.pack("<h", -32768)*80, **ARGS)
        self.assertEqual(p["segments"][0]["acoustic"]["rms"], 1.0)

    def test_reject_more_than_one_second(self):
        with self.assertRaises(ValueError):
            pcm16_to_a5(pcm=b"\\x00\\x00"*8001, **ARGS)

    def test_reject_bool_rate(self):
        with self.assertRaises(ValueError):
            pcm16_to_a5(pcm=b"\\x00\\x00"*80, **(ARGS | {"sample_rate": True}))

if __name__ == "__main__":
    unittest.main()
