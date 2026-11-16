import unittest
from v13.audio_percept import timed_audio_percept

REF={"source_id":"synthetic-fixture"}
FRAME=[{"start_ms":0,"end_ms":20,"rms":0.2,"pitch_hz":180,"voicing":0.7,"non_speech":False}]
class TimedAudioContractTest(unittest.TestCase):
    def test_timed_acoustics_without_asr(self):
        p=timed_audio_percept(REF,FRAME,consent=True,capture_id="synthetic",sample_rate_hz=16000)
        self.assertEqual(p["frames"][0]["acoustic"]["pitch_hz"],180)
        self.assertIsNone(p["teacher_ear"])
        self.assertEqual(p["learning_authority"],0)
    def test_permission_refusal(self):
        with self.assertRaises(PermissionError):
            timed_audio_percept(REF,FRAME,consent=False,capture_id="x",sample_rate_hz=16000)
    def test_timestamp_refusal(self):
        with self.assertRaises(ValueError):
            timed_audio_percept(REF,FRAME+[{"start_ms":10,"end_ms":30}],consent=True,capture_id="x",sample_rate_hz=16000)
    def test_nonfinite_refusal(self):
        with self.assertRaises(ValueError):
            timed_audio_percept(REF,[dict(FRAME[0],rms=float("nan"))],consent=True,capture_id="x",sample_rate_hz=16000)
    def test_teacher_not_truth(self):
        p=timed_audio_percept(REF,FRAME,consent=True,capture_id="x",sample_rate_hz=16000,teacher={"status":"FINAL","transcript":"hello"})
        self.assertEqual(p["teacher_ear"]["authority"],"UNTRUSTED_TEACHER_HYPOTHESIS")
if __name__=="__main__":unittest.main()
