"""Synthetic integration regressions: real V13 A5 admission consumer, not phone proof."""
import unittest
from dataclasses import replace
from v14.experiments.timed_perception import AudioSource, pcm_digest, timed_audio_packets
from v14.experiments.audio_v13_bridge import to_v13_a5_audio
from v13.a5_audio_admission_bridge import admit_audio

class V14AudioAdmissionIntegration(unittest.TestCase):
    def setUp(self):
        self.samples = [1000, -1000] * 400
        self.source = AudioSource("synthetic-audio", "synthetic-receipt", 1000,
                                  8000, len(self.samples), pcm_digest(self.samples))
    def test_real_v13_consumer_receives_windows(self):
        windows = timed_audio_packets(self.samples, self.source)
        percepts = to_v13_a5_audio(windows, self.source, consent_active=True)
        self.assertEqual(len(percepts), 3)
        from v13.percept_admission import admit
        admitted = admit(percepts, 1024)
        self.assertEqual(len(admitted.selected), 3)
        self.assertEqual(percepts[0].modality, "audio")
        self.assertTrue(percepts[0].final)
    def test_current_consent_revocation(self):
        with self.assertRaises(PermissionError):
            to_v13_a5_audio(timed_audio_packets(self.samples, self.source),
                            self.source, consent_active=False)
    def test_provisional_not_promoted(self):
        src = replace(self.source, provisional=True)
        p = to_v13_a5_audio(timed_audio_packets(self.samples, src), src, consent_active=True)
        self.assertFalse(p[0].final)
    def test_tampered_source_blocked(self):
        p = timed_audio_packets(self.samples, self.source)
        p[0]["pcm_sha256"] = "0"*64
        with self.assertRaises(PermissionError):
            to_v13_a5_audio(p, self.source, consent_active=True)
    def test_nonfinite_audio_feature_rejected(self):
        windows = timed_audio_packets(self.samples, self.source)
        windows[0]["rms"] = float("nan")
        with self.assertRaises(ValueError):
            to_v13_a5_audio(windows, self.source, consent_active=True)

    def test_v13_prompt_budget_is_bounded(self):
        from v13.a5_audio_admission_bridge import audio_to_admission
        windows = timed_audio_packets(self.samples, self.source)
        p = to_v13_a5_audio(windows, self.source, consent_active=True)
        self.assertEqual(len(p), 3)
        self.assertLess(len(p[0].summary), 128)

if __name__ == "__main__":
    unittest.main()
