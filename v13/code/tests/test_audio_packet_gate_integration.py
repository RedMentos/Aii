"""Cross-module A5 RAW EAR contract -> source gate regression (offline only).

No microphone permission, SQLite integration, or native Android inference is implied.
"""
import copy
import unittest

from v13.audio_percept_contract import audio_percept_packet
from v13.audio_source_gate import checked_audio_source_view
from v13.contracts import validate


KW = dict(
    event_id="synthetic-event",
    generation_id="synthetic-generation",
    source_id="synthetic-source",
    source_sha256="a" * 64,
    start_ms=0,
    end_ms=20,
    rms=0.2,
    zcr=0.1,
    consent_receipt="synthetic-consent-reference",
)
SOURCE = {"sha256": "a" * 64, "revoked": False, "modality": "audio"}


class PacketGateIntegrationTests(unittest.TestCase):
    def packet(self):
        p = audio_percept_packet(**KW)
        validate("PerceptPacket", p)
        return p

    def test_canonical_packet_consumed_in_shadow(self):
        result = checked_audio_source_view(self.packet(), lambda sid: SOURCE if sid == KW["source_id"] else None)
        self.assertEqual(result["authority"], "SHADOW_ONLY")
        self.assertEqual(result["segments"][0]["acoustic"]["rms"], 0.2)
        self.assertIsNone(result["segments"][0]["asr_transcript"])

    def test_revocation_after_packet_creation(self):
        p = self.packet()
        source = dict(SOURCE)
        checked_audio_source_view(p, lambda sid: source)
        source["revoked"] = True
        with self.assertRaises(PermissionError):
            checked_audio_source_view(p, lambda sid: source)

    def test_missing_consent_after_packet_creation(self):
        p = self.packet()
        del p["segments"][0]["consent_receipt_ref"]
        with self.assertRaises(PermissionError):
            checked_audio_source_view(p, lambda sid: SOURCE)

    def test_provisional_is_not_promoted(self):
        p = audio_percept_packet(**{**KW, "finality": "PROVISIONAL"})
        result = checked_audio_source_view(p, lambda sid: SOURCE)
        self.assertEqual(result["segments"][0]["finality"], "PROVISIONAL")
        self.assertEqual(result["authority"], "SHADOW_ONLY")

    def test_result_does_not_alias_packet(self):
        p = self.packet()
        original = copy.deepcopy(p)
        result = checked_audio_source_view(p, lambda sid: SOURCE)
        result["segments"][0]["acoustic"]["rms"] = 0.99
        result["source_ref"]["sha256"] = "b" * 64
        self.assertEqual(p, original)


if __name__ == "__main__":
    unittest.main()
