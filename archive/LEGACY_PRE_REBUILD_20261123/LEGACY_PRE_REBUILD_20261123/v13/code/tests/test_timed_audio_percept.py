import unittest
from v13.timed_audio_percept import TimedAudioPercept


def sample(**changes):
    args = dict(source_id="fixture-001", start_ms=100, end_ms=220,
                consent_scope="audio_observation_granted",
                provenance="raw_ear_derived", status="provisional",
                rms=0.2, pitch_hz=180.0, speech_probability=0.7,
                non_speech_probability=0.2, prosody_change=0.4,
                speaker_turn=False)
    args.update(changes)
    return TimedAudioPercept(**args)


class TimedAudioTests(unittest.TestCase):
    def test_acoustic_signal_not_reduced_to_asr(self):
        packet = sample()
        data = packet.bounded_context()
        self.assertEqual(data["modality"], "audio")
        self.assertEqual(data["prosody_change"], 0.4)
        self.assertNotIn("teacher_text", data)
        self.assertFalse(data["teacher_text_available"])

    def test_consent_required(self):
        with self.assertRaises(PermissionError):
            sample(consent_scope="off")

    def test_teacher_provenance(self):
        packet = sample(provenance="teacher_ear", status="final",
                        teacher_text="hello")
        self.assertTrue(packet.bounded_context()["teacher_text_available"])
        self.assertNotIn("hello", str(packet.bounded_context()))
        with self.assertRaises(ValueError):
            sample(teacher_text="hello")

    def test_time_and_feature_bounds(self):
        for kwargs in (dict(end_ms=100), dict(end_ms=11001),
                       dict(rms=float("nan")), dict(pitch_hz=float("inf")),
                       dict(speech_probability=1.1), dict(status="unknown")):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                sample(**kwargs)

    def test_distinct_non_speech_and_speaker_turn(self):
        packet = sample(speech_probability=0.05, non_speech_probability=0.9,
                        speaker_turn=True)
        self.assertEqual(packet.bounded_context()["non_speech_probability"], 0.9)
        self.assertTrue(packet.bounded_context()["speaker_turn"])


if __name__ == "__main__":
    unittest.main()
