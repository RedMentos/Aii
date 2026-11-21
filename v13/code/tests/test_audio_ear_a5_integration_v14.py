"""Integration regression for RAW EAR PCM16 -> strict A5 admission (synthetic only)."""
import struct
import unittest
from v13.audio_ear import observe_pcm16_for_a5
from v13.a5_audio_admission_bridge import audio_to_admission, admit_audio


class RawEarA5Integration(unittest.TestCase):
    def setUp(self):
        self.pcm = struct.pack("<" + "h" * 80, *([1000, -1000] * 40))
        self.kw = dict(consent=True, source_id="fixture:pcm", consent_receipt_ref="fixture:receipt")

    def packet(self):
        return observe_pcm16_for_a5(self.pcm, 8000, 1234, **self.kw)

    def test_real_producer_receiver_contract(self):
        packet = self.packet()
        percept = audio_to_admission(packet, consent_active=True)
        self.assertEqual(percept.modality, "audio")
        self.assertEqual(percept.start_ms, 1234)
        self.assertEqual(percept.end_ms, 1244)
        self.assertTrue(percept.final)
        self.assertNotIn("transcript", percept.summary.lower())
        self.assertFalse(packet["segments"][0]["learning_authority"])

    def test_revoked_consent(self):
        with self.assertRaises(PermissionError):
            audio_to_admission(self.packet(), consent_active=False)

    def test_no_capture_consent(self):
        with self.assertRaises(PermissionError):
            observe_pcm16_for_a5(self.pcm, 8000, 0, **{**self.kw, "consent":False})

    def test_receipt_required(self):
        with self.assertRaises(PermissionError):
            observe_pcm16_for_a5(self.pcm, 8000, 0, **{**self.kw, "consent_receipt_ref":""})

    def test_over_budget_rejected(self):
        with self.assertRaises(ValueError):
            observe_pcm16_for_a5(b"\\0\\0" * 8001, 8000, 0, **self.kw)

    def test_provisional_not_final(self):
        packet = self.packet()
        packet["segments"][0]["finality"] = "PROVISIONAL"
        self.assertFalse(audio_to_admission(packet, consent_active=True).final)

    def test_no_authority_escalation(self):
        packet = self.packet()
        packet["segments"][0]["action_authority"] = True
        with self.assertRaises(PermissionError):
            audio_to_admission(packet, consent_active=True)


if __name__ == "__main__":
    unittest.main()
