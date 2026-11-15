import unittest
from timed_audio import TimedAudioPercept, ordered_percepts

def event(**kw):
    d = dict(source_id="fixture-1", consent_scope="synthetic-only", start_ms=0,
             end_ms=20, rms=.3, voiced_fraction=.6, spectral_centroid_hz=700)
    d.update(kw)
    return TimedAudioPercept(**d)

class AudioContractTest(unittest.TestCase):
    def test_acoustic_without_asr(self):
        a = event().to_a5()
        self.assertEqual(a["modality"], "audio_acoustic")
        self.assertIsNone(a["teacher_transcript"])
        self.assertEqual(a["gate"], "SHADOW")
    def test_teacher_final(self):
        self.assertEqual(event(final=True, transcript="hello").to_a5()["teacher_transcript"], "hello")
        with self.assertRaises(ValueError):
            event(transcript="premature")
    def test_invalid(self):
        for kw in ({"rms": float("nan")}, {"voiced_fraction": 1.1},
                   {"consent_scope": ""}, {"start_ms": 21}, {"provenance": "covert"}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                event(**kw)
    def test_ordering(self):
        self.assertEqual(len(list(ordered_percepts([event(), event(start_ms=20, end_ms=40)]))), 2)
        with self.assertRaises(ValueError):
            list(ordered_percepts([event(), event(start_ms=19, end_ms=40)]))

if __name__ == "__main__":
    unittest.main()
