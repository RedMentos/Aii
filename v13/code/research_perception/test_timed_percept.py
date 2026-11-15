import unittest
from timed_percept import TimedPercept, audio_fixture, ui_fixture

class TestTimedPercept(unittest.TestCase):
    def test_audio_keeps_acoustics_without_asr(self):
        p = audio_fixture([0.5, -0.5, 0.5, -0.5], 1000, 10, 'microphone.fixture')
        self.assertEqual(p.to_packet()['schema'], 'v13.a5.timed-percept/1')
        self.assertIsNone(p.teacher_text)
        self.assertGreater(p.features['rms'], 0)
        self.assertEqual(p.to_packet()['gate'], 'SYNTHETIC_ONLY')
    def test_provisional_teacher_not_replace_raw(self):
        p = audio_fixture([0.1]*10, 1000, 0, 'audio.fixture', teacher_text='maybe')
        self.assertEqual(p.teacher_text, 'maybe')
        self.assertEqual(p.features['sample_count'], 10)
        self.assertEqual(p.phase, 'provisional')
    def test_ui_no_action_authority(self):
        self.assertFalse(ui_fixture(0, 5, 'ui.fixture', node_count=2).features['action_authority'])
    def test_denies_missing_consent(self):
        with self.assertRaises(PermissionError):
            audio_fixture([0.1], 1000, 0, '')
    def test_denies_bad_timing(self):
        with self.assertRaises(ValueError):
            TimedPercept('audio','fixture',2,2,'fixture','synthetic','final',{})
    def test_denies_bad_phase(self):
        with self.assertRaises(ValueError):
            audio_fixture([0.1], 1000, 0, 'fixture', phase='unknown')
    def test_denies_bad_samples(self):
        with self.assertRaises(ValueError):
            audio_fixture([1.5], 1000, 0, 'fixture')
    def test_denies_unbounded_fixture(self):
        with self.assertRaises(ValueError):
            audio_fixture([0.0]*10001, 1000, 0, 'fixture')
    def test_denies_ui_teacher_text(self):
        with self.assertRaises(ValueError):
            TimedPercept('android_ui','fixture',0,1,'fixture','synthetic','final',{},'oops')

if __name__ == '__main__':
    unittest.main()
