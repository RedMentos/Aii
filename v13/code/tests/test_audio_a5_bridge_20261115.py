"""Synthetic-only A5/RAW EAR bridge contract tests."""
import unittest
from dataclasses import replace
from v13.audio_raw_ear_contract import synthetic_pcm_packet
from v13.audio_a5_bridge import to_a5_audio, finalize_audio


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.old = synthetic_pcm_packet([-.2, .2] * 80, source_id="fixture", start_ms=100, phase="provisional")

    def test_acoustic_nonverbal_retained_in_raw(self):
        a5 = to_a5_audio(self.old)
        self.assertEqual(a5.modality, "audio")
        self.assertEqual(a5.source, self.old.source_id)
        self.assertEqual(a5.rms, self.old.rms)
        self.assertIsNone(a5.transcript)
        self.assertGreater(self.old.zero_crossing_rate, 0)

    def test_valid_final(self):
        new = replace(self.old, phase="final")
        self.assertEqual(finalize_audio(self.old, new)["stage"], "final")

    def test_cross_consent_rejected(self):
        with self.assertRaises(ValueError):
            finalize_audio(self.old, replace(self.old, phase="final", consent_scope="other"))

    def test_cross_source_rejected(self):
        with self.assertRaises(ValueError):
            finalize_audio(self.old, replace(self.old, phase="final", source_id="other"))

    def test_regressed_end_rejected(self):
        with self.assertRaises(ValueError):
            finalize_audio(self.old, replace(self.old, phase="final", end_ms=self.old.end_ms-1))

    def test_format_change_rejected(self):
        with self.assertRaises(ValueError):
            finalize_audio(self.old, replace(self.old, phase="final", sample_rate_hz=8000))

    def test_teacher_revision_source_bound(self):
        new = replace(self.old, phase="final", teacher_transcript="example", teacher_revision="fixture-v1")
        self.assertEqual(finalize_audio(self.old, new)["provenance"], "teacher")

    def test_invalid_teacher_without_revision_rejected(self):
        with self.assertRaises(ValueError):
            to_a5_audio(replace(self.old, teacher_transcript="example"))


if __name__ == "__main__":
    unittest.main()
