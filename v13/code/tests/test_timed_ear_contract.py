"""Offline contract tests; never imply microphone or Redmi validation."""
import unittest
from v13.timed_ear_contract import AcousticFrame, TimedEarPacket


class TimedEarContractTests(unittest.TestCase):
    def frame(self, start=0, end=20, **kwargs):
        return AcousticFrame(start, end, kwargs.get("rms", .25),
                             kwargs.get("pitch_hz", 180.0),
                             kwargs.get("speech_probability", .7),
                             kwargs.get("non_speech", ("breath",)),
                             kwargs.get("provisional", True))

    def test_nonverbal_and_provisional_survive(self):
        p = TimedEarPacket("synthetic", "synthetic_test", (self.frame(),))
        a = p.percept_packet()
        self.assertEqual(a["acoustics"][0]["non_speech"], ["breath"])
        self.assertTrue(a["provisional"])
        self.assertIsNone(a["teacher_asr"])
        self.assertFalse(a["action_authority"])
        self.assertEqual(a["a3_projector"], "UNAVAILABLE")

    def test_final_teacher_provenance(self):
        p = TimedEarPacket("synthetic", "synthetic_test",
                           (self.frame(provisional=False),), transcript="hello",
                           teacher_revision="frozen-test")
        self.assertFalse(p.percept_packet()["provisional"])
        self.assertEqual(p.percept_packet()["teacher_asr"]["revision"], "frozen-test")

    def test_live_requires_consent(self):
        with self.assertRaises(PermissionError):
            TimedEarPacket("authorized_microphone", "synthetic_test", (self.frame(),))
        with self.assertRaises(PermissionError):
            TimedEarPacket("authorized_feed", "off", (self.frame(),))

    def test_overlap_rejected(self):
        with self.assertRaises(ValueError):
            TimedEarPacket("synthetic", "synthetic_test",
                           (self.frame(0, 20), self.frame(10, 30)))

    def test_invalid_acoustic_rejected(self):
        for bad in (float("nan"), float("inf"), -1, 1.1):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.frame(rms=bad)

    def test_missing_asr_teacher_rejected(self):
        with self.assertRaises(ValueError):
            TimedEarPacket("synthetic", "synthetic_test", (self.frame(),), transcript="hello")

    def test_bounded_frames(self):
        with self.assertRaises(ValueError):
            TimedEarPacket("synthetic", "synthetic_test", (self.frame(),) * 129)


if __name__ == "__main__":
    unittest.main()
