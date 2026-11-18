import unittest
from v13.percept_admission import admit,verify

class PerceptAdmissionTests(unittest.TestCase):
    def test_source_exact_and_budget(self):
        s="first sentence; second sentence"
        p=admit(s,"a5:1",budget=10,consent=True)
        self.assertEqual(p.text,"first sent")
        self.assertTrue(verify(p,s))
        self.assertFalse(verify(p,s.replace("sent","lost")))
        self.assertTrue(p.truncated)
    def test_reentry(self):
        s="123456789"
        a=admit(s,"a5:2",budget=4,consent=True)
        b=admit(s,"a5:2",budget=4,start=a.end,consent=True)
        self.assertEqual(a.text+b.text,"12345678")
        self.assertTrue(verify(b,s))
    def test_permission(self):
        with self.assertRaises(PermissionError):
            admit("private","ear:1",budget=8)
    def test_invalid(self):
        for n in (0,-1,True):
            with self.assertRaises(ValueError):
                admit("x","a5:1",budget=n,consent=True)
    def test_audio_not_asr_only(self):
        p=admit("pitch=180Hz;pause=200ms","ear:3",budget=32,modality="audio",consent=True)
        self.assertTrue(verify(p,"pitch=180Hz;pause=200ms"))
if __name__=="__main__": unittest.main()
