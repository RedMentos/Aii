import unittest
from v13.audio_admission import AcousticFrame,admit_audio

class AcousticAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.frames=[AcousticFrame(0,20,.2,220,True,provisional=True),
                     AcousticFrame(20,40,.3,None,False,"breath",provisional=False)]
    def call(self,**kw):
        return admit_audio(self.frames,consent=True,source_id="synthetic-fixture",**kw)
    def test_provenance_and_nonverbal(self):
        packet=self.call()
        self.assertTrue(packet["accepted"])
        self.assertEqual(packet["frames"][1]["non_speech"],"breath")
        self.assertEqual(packet["frames"][0]["provenance"],"PROVISIONAL")
        self.assertFalse(packet["raw_audio_included"])
        self.assertFalse(packet["teacher_asr_authority"])
        self.assertEqual(packet["sha256"],self.call()["sha256"])
    def test_no_consent(self):
        with self.assertRaises(PermissionError):
            admit_audio(self.frames,consent=False,source_id="synthetic-fixture")
    def test_budget_no_silent_truncation(self):
        self.assertEqual(self.call(max_frames=1)["status"],"REJECTED_BUDGET")
        many=[AcousticFrame(i*20,(i+1)*20,.1) for i in range(15)]
        self.assertEqual(admit_audio(many,consent=True,source_id="fixture",max_bytes=256)["status"],"REJECTED_BUDGET")
    def test_invalid_timing(self):
        with self.assertRaises(ValueError):
            admit_audio([self.frames[1],self.frames[0]],consent=True,source_id="fixture")
    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            admit_audio([AcousticFrame(0,20,float("nan"))],consent=True,source_id="fixture")
    def test_empty_source_rejected(self):
        with self.assertRaises(ValueError):
            admit_audio(self.frames,consent=True,source_id="")
if __name__=="__main__":
    unittest.main()
