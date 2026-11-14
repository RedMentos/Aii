"""Negative boundary tests for the A5 audio envelope; no microphone access."""
import unittest
from v13.timed_ear_contract import AcousticFrame, TimedEarPacket


class EarAdversarialTests(unittest.TestCase):
    def frame(self, **kw):
        d = dict(start_ms=0, end_ms=20, rms=.2, pitch_hz=180.0,
                 speech_probability=.8, non_speech=("breath",))
        d.update(kw)
        return AcousticFrame(**d)

    def test_bool_timestamps_rejected(self):
        for kw in ({"start_ms": False}, {"end_ms": True}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                self.frame(**kw)

    def test_nonnumeric_acoustics_rejected(self):
        for field in ("rms", "pitch_hz", "speech_probability"):
            for bad in ("0.4", True, object()):
                with self.subTest(field=field, bad=type(bad).__name__), self.assertRaises(ValueError):
                    self.frame(**{field: bad})

    def test_empty_nonspeech_label_rejected(self):
        with self.assertRaises(ValueError):
            self.frame(non_speech=("",))

    def test_teacher_revision_bounded(self):
        with self.assertRaises(ValueError):
            TimedEarPacket("synthetic", "synthetic_test", (self.frame(),),
                           transcript="test", teacher_revision="x" * 129)

    def test_valid_derived_packet_preserves_nonverbal(self):
        packet = TimedEarPacket("synthetic", "synthetic_test", (self.frame(),))
        out = packet.percept_packet()
        self.assertEqual(out["acoustics"][0]["non_speech"], ["breath"])
        self.assertFalse(out["action_authority"])
        self.assertEqual(out["a3_projector"], "UNAVAILABLE")

if __name__ == "__main__":
    unittest.main()
