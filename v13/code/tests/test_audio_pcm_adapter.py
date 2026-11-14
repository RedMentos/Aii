"""Synthetic PCM fixture; never interpreted as microphone/Redmi proof."""
import unittest
from v13.audio_pcm_adapter import pcm16_to_a5

ARGS = dict(sample_rate=8000, start_ms=100, event_id="fixture-event",
            generation_id="fixture-generation", source_id="fixture-source",
            source_sha256="a"*64, consent_receipt="local-fixture-only")

class TestPCMAdapter(unittest.TestCase):
    def test_zero_signal_preserves_source_and_timing(self):
        p = pcm16_to_a5(pcm=b"\\x00\\x00"*80, **ARGS)
        self.assertEqual(p["segments"][0]["start_ms"], 100)
        self.assertEqual(p["segments"][0]["end_ms"], 110)
        self.assertEqual(p["segments"][0]["acoustic"]["rms"], 0)
        self.assertFalse(p["segments"][0]["learning_authority"])

    def test_alternating_signal_has_crossings(self):
        pcm = (b"\\xff\\x7f\\x00\\x80")*40
        p = pcm16_to_a5(pcm=pcm, **ARGS)
        self.assertGreater(p["segments"][0]["acoustic"]["zcr"], 0.9)

    def test_rejects_missing_consent(self):
        with self.assertRaises(PermissionError):
            pcm16_to_a5(pcm=b"\\x00\\x00"*80, **(ARGS | {"consent_receipt":None}))

    def test_rejects_malformed_or_too_short(self):
        for pcm in (b"", b"\\x00", b"\\x00\\x00"):
            with self.subTest(pcm=pcm), self.assertRaises(ValueError):
                pcm16_to_a5(pcm=pcm, **ARGS)

if __name__ == "__main__":
    unittest.main()
