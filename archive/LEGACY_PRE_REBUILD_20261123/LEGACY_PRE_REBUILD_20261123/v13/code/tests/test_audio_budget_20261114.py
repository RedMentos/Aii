"""Offline synthetic A5 budget tests; no native device or audio model claims."""
import unittest
from v13.audio_budget import summarize_acoustics
from v13.timed_ear_contract import AcousticFrame, TimedEarPacket


def packet(n=12, teacher=False):
    frames = tuple(AcousticFrame(i*20, (i+1)*20, .1, 180.0,
        .99 if i == 6 else .2, ("cough",) if i == 5 else (), True)
        for i in range(n))
    return TimedEarPacket("synthetic", "synthetic_test", frames,
        transcript="test" if teacher else None,
        teacher_revision="frozen" if teacher else None)


class AudioBudgetTests(unittest.TestCase):
    def test_boundary_salience_and_loss(self):
        x = summarize_acoustics(packet(), 4)
        self.assertEqual([f["start_ms"] for f in x["acoustics"]], [0, 100, 120, 220])
        self.assertEqual(x["omitted_frames"], 8)
        self.assertTrue(x["lossy"])
        self.assertFalse(x["action_authority"])

    def test_no_loss_under_budget(self):
        x = summarize_acoustics(packet(2), 2)
        self.assertFalse(x["lossy"])
        self.assertEqual(x["omitted_frames"], 0)

    def test_bad_budget(self):
        for n in (True, 1, 33, 2.0):
            with self.subTest(n=n), self.assertRaises(ValueError):
                summarize_acoustics(packet(), n)

    def test_teacher_and_consent_provenance(self):
        x = summarize_acoustics(packet(12, True))
        self.assertEqual(x["teacher_asr"]["revision"], "frozen")
        self.assertEqual(x["consent_scope"], "synthetic_test")
        self.assertEqual(x["a3_projector"], "UNAVAILABLE")

    def test_deterministic(self):
        self.assertEqual(summarize_acoustics(packet()), summarize_acoustics(packet()))


if __name__ == "__main__":
    unittest.main()
