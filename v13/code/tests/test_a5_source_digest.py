"""Regression: A5 source identity survives audio -> admission -> C3 selection.

Synthetic only. Does not test microphone, native inference or Android consent.
"""
import unittest
from v13.a5_audio_admission_bridge import audio_to_admission, admit_audio
from v13.percept_admission import Percept, admit


class AudioSourceDigestTests(unittest.TestCase):
    def packet(self, digest="a" * 64, finality="FINAL"):
        return {
            "modality": "audio",
            "source_ref": {"source_id": "synthetic-frame-1", "sha256": digest},
            "segments": [{
                "consent_receipt_ref": "synthetic-opt-in",
                "start_ms": 0, "end_ms": 20, "finality": finality,
                "acoustic": {"rms": 0.25, "zcr": 0.1},
                "learning_authority": False, "action_authority": False,
            }],
        }

    def test_digest_survives_to_admitted_observation(self):
        packet = self.packet()
        result = admit_audio(packet, consent_active=True, token_budget=1024)
        self.assertEqual(result.status, "ADMITTED")
        self.assertEqual(result.selected[0].source_sha256, packet["source_ref"]["sha256"])

    def test_provisional_never_promoted(self):
        result = admit_audio(self.packet(finality="PROVISIONAL"),
                             consent_active=True, token_budget=1024)
        self.assertEqual(result.selected, ())
        self.assertEqual(result.omitted, ("synthetic-frame-1",))

    def test_current_consent_required(self):
        with self.assertRaises(PermissionError):
            audio_to_admission(self.packet(), consent_active=False)

    def test_malformed_digest_rejected(self):
        with self.assertRaises(ValueError):
            audio_to_admission(self.packet(digest="not-a-hash"), consent_active=True)
        with self.assertRaises(ValueError):
            admit((Percept("id", "audio", 0, 20, "test", True, True,
                          source_sha256="z" * 64),), 1024)

    def test_legacy_text_percept_unchanged(self):
        result = admit((Percept("text-id", "text", 0, 0, "hello", True, True),), 1024)
        self.assertEqual(result.selected[0].source_sha256, "")


if __name__ == "__main__":
    unittest.main()
