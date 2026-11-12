"""Focused host-only A5 candidate tests; no native Android claims."""
import unittest
from v13.a5_audio_envelope import from_timed_a3

def fixture():
    return {"a5": {
        "source_id": "synthetic-1", "source_sha256": "a"*64,
        "store_source_sha256": "b"*64, "a3_embedding": [0.2, -0.1],
        "a3_training_steps": 3, "status": "SHADOW_TIMED_AUDIO",
        "authority": "observation_only", "android_action_allowed": False,
        "provisional": False, "start_ms": 0, "end_ms": 20, "sample_rate_hz": 16000,
        "acoustic": {"rms": 0.3, "pitch_hz": 0, "speech_probability": 0},
        "transcript": None,
        "a4_salience": {"score": 0.25, "method": "bounded_rms_zcr_heuristic",
                        "learned": False, "authority": "observation_only",
                        "unmeasured": ["pitch_hz", "speech_probability", "speaker_identity"]}
    }}

class AudioEnvelopeTests(unittest.TestCase):
    def test_preserves_nonverbal_and_missing_measurements(self):
        x = from_timed_a3(fixture())
        self.assertEqual(x["raw_ear"]["rms"], 0.3)
        self.assertIn("pitch_hz", x["raw_ear"]["unmeasured"])
        self.assertIsNone(x["transcript"])
        self.assertFalse(x["canonical_a5"])
        self.assertFalse(x["android_action_allowed"])
        self.assertEqual(x["runtime_consumer"], "NOT_CONNECTED")

    def test_refuses_action_or_provisional(self):
        for key, value in (("android_action_allowed", True), ("provisional", True)):
            x = fixture()
            x["a5"][key] = value
            with self.assertRaises(PermissionError):
                from_timed_a3(x)

    def test_refuses_nonfinite_and_bad_provenance(self):
        for key, value in (("a3_embedding", [float("nan")]),
                           ("store_source_sha256", "bad"),
                           ("start_ms", 20)):
            x = fixture()
            x["a5"][key] = value
            with self.assertRaises(ValueError):
                from_timed_a3(x)

    def test_no_fabricated_transcript(self):
        x = fixture()
        x["a5"]["transcript"] = "invented"
        with self.assertRaises(ValueError):
            from_timed_a3(x)

if __name__ == "__main__":
    unittest.main()
