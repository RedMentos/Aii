import unittest
from v13.audio_timeline import build_audio_percept
REF={'source_id':'synthetic-1','sha256':'a'*64}
F={'start_ms':0,'end_ms':20,'rms':0.2,'pitch_hz':110,'voicing':0.6,'speech_probability':0.8,'non_speech':'breath'}
class TestAudioTimeline(unittest.TestCase):
    def test_nonverbal_without_asr(self):
        p=build_audio_percept(REF,[F],consent=True,source_kind='synthetic_fixture')
        self.assertEqual(p['frames'][0]['non_speech'],'breath')
        self.assertIsNone(p['teacher_asr'])
        self.assertEqual(p['learning_authority'],0)
    def test_consent(self):
        with self.assertRaises(PermissionError):build_audio_percept(REF,[F],consent=False)
    def test_overlap(self):
        with self.assertRaises(ValueError):build_audio_percept(REF,[F,dict(F,start_ms=10,end_ms=30)],consent=True)
    def test_nan(self):
        with self.assertRaises(ValueError):build_audio_percept(REF,[dict(F,rms=float('nan'))],consent=True)
    def test_teacher_is_not_truth(self):
        p=build_audio_percept(REF,[F],consent=True,teacher_text='hello',final=True)
        self.assertEqual(p['teacher_asr']['authority'],'UNVERIFIED_TEACHER_HINT')
    def test_source_hash_validation(self):
        with self.assertRaises(ValueError):
            build_audio_percept({'source_id':'x','sha256':'not-a-hash'},[F],consent=True)
    def test_bounded_frame_count(self):
        with self.assertRaises(ValueError):
            build_audio_percept(REF,[F]*4097,consent=True)
    def test_label_validation(self):
        with self.assertRaises(ValueError):
            build_audio_percept(REF,[dict(F,non_speech={'unexpected':'object'})],consent=True)
if __name__=='__main__':unittest.main()
