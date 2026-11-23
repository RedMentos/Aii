import unittest
from v13.acoustic_percept_adapter import AcousticFrame, acoustic_to_percept
from v13.percept_admission import admit


def frame(**kw):
    x = dict(source_id="fixture:1", start_ms=0, end_ms=20, rms=.2,
             pitch_hz=180., speech_probability=.1, non_speech="laughter",
             consent=True, final=True)
    x.update(kw)
    return AcousticFrame(**x)


class AcousticAdapterTests(unittest.TestCase):
    def test_nonverbal_and_lineage(self):
        p = acoustic_to_percept(frame())
        self.assertIn("laughter", p.summary)
        self.assertEqual(p.source_id, "fixture:1")
        self.assertEqual(p.modality, "audio")

    def test_provisional_stays_out_of_final_prompt(self):
        p = acoustic_to_percept(frame(final=False))
        self.assertEqual(admit([p], 1000).selected, ())

    def test_consent_stays_out(self):
        p = acoustic_to_percept(frame(consent=False))
        self.assertEqual(admit([p], 1000).selected, ())

    def test_invalid_features(self):
        for kw in (dict(rms=float("nan")), dict(pitch_hz=-1),
                   dict(speech_probability=1.2), dict(non_speech="secret"),
                   dict(end_ms=-1)):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                acoustic_to_percept(frame(**kw))

    def test_no_asr_transcript(self):
        self.assertNotIn("transcript", acoustic_to_percept(frame()).summary)


if __name__ == "__main__":
    unittest.main()
