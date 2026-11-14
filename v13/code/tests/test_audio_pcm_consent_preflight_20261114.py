"""Synthetic consent preflight regression. Not a Redmi microphone test."""
import unittest
from v13.audio_pcm_adapter import pcm16_to_a5

KW = dict(sample_rate=8000, start_ms=0, event_id="e", generation_id="g",
          source_id="source", source_sha256="a"*64)

class ConsentPreflightTests(unittest.TestCase):
    def test_denied_consent_precedes_malformed_pcm(self):
        # No raw input should be traversed when authorization is absent.
        for receipt in (None, "", "  ", False, 1):
            with self.subTest(receipt=receipt):
                with self.assertRaises(PermissionError):
                    pcm16_to_a5(pcm=object(), consent_receipt=receipt, **KW)

    def test_authorized_malformed_pcm_still_rejected(self):
        with self.assertRaises(TypeError):
            pcm16_to_a5(pcm=object(), consent_receipt="synthetic-only", **KW)

if __name__ == "__main__":
    unittest.main()
