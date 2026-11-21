"""Offline tests: python -m unittest discover -s v13/code/tests -p 'test_timed_raw_ear_contract.py'"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13.timed_raw_ear_contract import EarFrame, to_percept_packet


class TimedRawEarTests(unittest.TestCase):
    def packet(self, frame=None, **kwargs):
        return to_percept_packet(frame or EarFrame("fixture:1", 0, 20, 0.2), **({"consent": True, "source_authorized": True} | kwargs))

    def test_acoustics_without_asr(self):
        p = self.packet(EarFrame("fixture:1", 0, 20, 0.2, pitch_hz=170,
                                 non_speech_label="laugh", final=False))
        self.assertEqual(p["acoustics"]["non_speech"], "laugh")
        self.assertIsNone(p["teacher"])
        self.assertEqual(p["status"], "PROVISIONAL")
        self.assertFalse(p["action_authority"])

    def test_final_teacher_provenance(self):
        p = self.packet(EarFrame("fixture:1", 20, 40, 0.1, transcript="hello",
                                 teacher_revision="fixture-teacher-v1", final=True))
        self.assertEqual(p["status"], "FINAL")
        self.assertEqual(p["teacher"]["revision"], "fixture-teacher-v1")

    def test_consent_is_required(self):
        for kw in ({"consent": False}, {"source_authorized": False}):
            with self.subTest(kw=kw), self.assertRaises(PermissionError):
                self.packet(**kw)

    def test_invalid_intervals_and_numeric_bounds(self):
        for frame in (EarFrame("x", 10, 10, .1), EarFrame("x", 0, 30001, .1),
                      EarFrame("x", 0, 1, float("nan")), EarFrame("x", 0, 1, 2.0),
                      EarFrame("x", 0, 1, .1, voiced_probability=1.5)):
            with self.subTest(frame=frame), self.assertRaises(ValueError):
                self.packet(frame)

    def test_transcript_requires_teacher_revision(self):
        with self.assertRaises(ValueError):
            self.packet(EarFrame("x", 0, 20, .1, transcript="unknown source"))


if __name__ == "__main__":
    unittest.main()
