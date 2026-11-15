"""Synthetic A5 audio admission boundary tests; no microphone or Redmi evidence."""
import unittest
from v13.a5_audio_admission_bridge import audio_to_admission, admit_audio


def fixture():
    return {
        "modality": "audio",
        "source_ref": {"source_id": "fixture-1", "sha256": "a" * 64},
        "segments": [{
            "consent_receipt_ref": "local-receipt",
            "start_ms": 100, "end_ms": 200, "finality": "FINAL",
            "acoustic": {"rms": 0.25, "zcr": 0.125},
            "learning_authority": False, "action_authority": False,
            "asr_transcript": None,
        }],
    }


class AudioAdmissionBoundary(unittest.TestCase):
    def test_final_audio_preserves_source_and_acoustics(self):
        candidate = audio_to_admission(fixture(), consent_active=True)
        self.assertEqual(candidate.source_id, "fixture-1")
        self.assertIn("rms=0.250", candidate.summary)
        self.assertIn("zcr=0.125", candidate.summary)
        self.assertNotIn("transcript", candidate.summary)

    def test_revoked_permission_denies_even_with_receipt(self):
        with self.assertRaises(PermissionError):
            audio_to_admission(fixture(), consent_active=False)

    def test_truthy_permission_not_accepted(self):
        with self.assertRaises(PermissionError):
            audio_to_admission(fixture(), consent_active="yes")

    def test_provisional_is_not_promoted(self):
        p = fixture()
        p["segments"][0]["finality"] = "PROVISIONAL"
        self.assertFalse(audio_to_admission(p, consent_active=True).final)
        self.assertEqual(admit_audio(p, consent_active=True, token_budget=1024).selected, ())

    def test_small_budget_omits_without_truncating(self):
        result = admit_audio(fixture(), consent_active=True, token_budget=1)
        self.assertEqual(result.selected, ())
        self.assertEqual(result.omitted, ("fixture-1",))

    def test_nonfinite_feature_rejected(self):
        p = fixture()
        p["segments"][0]["acoustic"]["rms"] = float("nan")
        with self.assertRaises(ValueError):
            audio_to_admission(p, consent_active=True)

    def test_authority_escalation_rejected(self):
        p = fixture()
        p["segments"][0]["action_authority"] = True
        with self.assertRaises(PermissionError):
            audio_to_admission(p, consent_active=True)

    def test_boolean_timestamp_rejected(self):
        p = fixture()
        p["segments"][0]["start_ms"] = True
        with self.assertRaises(ValueError):
            audio_to_admission(p, consent_active=True)

    def test_source_hash_required(self):
        p = fixture()
        p["source_ref"]["sha256"] = "unknown"
        with self.assertRaises(ValueError):
            audio_to_admission(p, consent_active=True)


if __name__ == "__main__":
    unittest.main()
