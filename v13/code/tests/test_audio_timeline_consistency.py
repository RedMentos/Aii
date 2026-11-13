"""Regression for A5 acoustic temporal consistency; synthetic only, no Android claims."""
import unittest
from v13.audio_prompt_admission import admit_audio_shadow

def packet():
    return {
        "kind": "A5_AUDIO_OBSERVATION", "authority": "SHADOW_ONLY",
        "action_authority": False, "learning_authority": False,
        "semantic_truth_authority": False, "finality": "FINAL",
        "source_ref": {"source_id": "fixture", "sha256": "a" * 64},
        "windows": [
            {"start_ms": 0, "end_ms": 20, "rms": .2, "zcr": .1, "finality": "FINAL"},
            {"start_ms": 20, "end_ms": 40, "rms": .3, "zcr": .2, "finality": "FINAL"},
        ],
    }

class AudioTimelineConsistencyTests(unittest.TestCase):
    def test_adjacent_final_windows_allowed(self):
        self.assertEqual(admit_audio_shadow(packet(), max_utf8_bytes=1024)["status"], "FULL")

    def test_gapped_final_windows_allowed(self):
        p = packet()
        p["windows"][1]["start_ms"] = 25
        self.assertEqual(admit_audio_shadow(p, max_utf8_bytes=1024)["status"], "FULL")

    def test_overlap_rejected(self):
        p = packet()
        p["windows"][1]["start_ms"] = 19
        with self.assertRaisesRegex(ValueError, "overlapping"):
            admit_audio_shadow(p)

    def test_reversed_windows_rejected(self):
        p = packet()
        p["windows"].reverse()
        with self.assertRaisesRegex(ValueError, "overlapping"):
            admit_audio_shadow(p)

    def test_final_claim_with_provisional_window_rejected(self):
        p = packet()
        p["windows"][1]["finality"] = "PROVISIONAL"
        with self.assertRaisesRegex(ValueError, "provisional"):
            admit_audio_shadow(p)

    def test_provisional_packet_with_mixed_windows_allowed(self):
        p = packet()
        p["finality"] = "PROVISIONAL"
        p["windows"][1]["finality"] = "PROVISIONAL"
        self.assertEqual(admit_audio_shadow(p, max_utf8_bytes=1024)["status"], "FULL")

    def test_invalid_timeline_rejected_even_if_budget_zero(self):
        p = packet()
        p["windows"][1]["start_ms"] = 1
        with self.assertRaises(ValueError):
            admit_audio_shadow(p, max_utf8_bytes=0)

if __name__ == "__main__":
    unittest.main()
