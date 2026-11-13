"""Regression: A5 audio consumers must not accept forged packet-level authority.

Synthetic only; no microphone, Android consent, or model training.
"""
import unittest

from v13.audio_percept_contract import audio_percept_packet
from v13.audio_shadow_consumer import audio_shadow_observation


class AudioTopLevelAuthorityTests(unittest.TestCase):
    def packet(self):
        return audio_percept_packet(
            event_id="synthetic-event", generation_id="synthetic-generation",
            source_id="synthetic-source", source_sha256="a" * 64,
            start_ms=0, end_ms=20, rms=0.2, zcr=0.1,
            consent_receipt="synthetic-receipt-not-os-consent",
        )

    def read_source(self, source_id):
        self.assertEqual(source_id, "synthetic-source")
        return {"sha256": "a" * 64, "revoked": False, "modality": "audio"}

    def test_unmodified_packet_remains_shadow(self):
        result = audio_shadow_observation(self.packet(), self.read_source)
        self.assertEqual(result["authority"], "SHADOW_ONLY")
        self.assertFalse(result["action_authority"])
        self.assertFalse(result["learning_authority"])

    def test_forged_top_level_authorities_rejected(self):
        for field in ("action_authority", "learning_authority",
                      "semantic_truth_authority"):
            with self.subTest(field=field):
                forged = self.packet()
                forged[field] = True
                with self.assertRaises(PermissionError):
                    audio_shadow_observation(forged, self.read_source)

    def test_forged_top_level_authority_label_rejected(self):
        forged = self.packet()
        forged["authority"] = "ACTIVE"
        with self.assertRaises(PermissionError):
            audio_shadow_observation(forged, self.read_source)


if __name__ == "__main__":
    unittest.main()
