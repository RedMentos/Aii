import unittest
from v13.timed_ear import timed_ear_packet, deliver_to_jef
class Store:
    def __init__(self): self.events=[]
    def log(self,k,e,p): self.events.append((k,p))
class Runtime:
    def __init__(self): self.store=Store()
class Tests(unittest.TestCase):
    def setUp(self): self.frames=[{"start_ms":0,"end_ms":20,"rms":.1,"voicing":.7},{"start_ms":20,"end_ms":40,"speech_probability":.9}]
    def test_delivery(self):
        r=Runtime();p=timed_ear_packet("local:1",self.frames,consent=True,teacher={"kind":"ASR","source_ref":"local:1","model_revision":"test"})
        self.assertEqual(deliver_to_jef(r,p,consent=True)["frames"],2)
        self.assertEqual(r.store.events[0][0],"a5_timed_ear_observed")
    def test_consent(self):
        with self.assertRaises(PermissionError):timed_ear_packet("local:1",self.frames,consent=False)
        with self.assertRaises(PermissionError):deliver_to_jef(Runtime(),timed_ear_packet("local:1",self.frames,consent=True),consent=False)
    def test_order(self):
        with self.assertRaises(ValueError):timed_ear_packet("local:1",self.frames[::-1],consent=True)
    def test_nan(self):
        with self.assertRaises(ValueError):timed_ear_packet("local:1",[{"start_ms":0,"end_ms":20,"rms":float("nan")}],consent=True)
    def test_source(self):
        with self.assertRaises(ValueError):timed_ear_packet("local:1",self.frames,consent=True,teacher={"kind":"ASR","source_ref":"other","model_revision":"t"})
    def test_bounds(self):
        with self.assertRaises(ValueError):timed_ear_packet("local:1",self.frames*129,consent=True)
if __name__=="__main__":unittest.main()
