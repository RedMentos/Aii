import unittest
from unittest.mock import patch
from v13.cognition import Cognition

class Store:
    def __init__(self):self.saved=[];self.logs=[]
    def read_source(self,ref):
        if ref.get("source_id")!="fixture":raise ValueError("revoked source")
        return "authorized audio source"
    def add_packet(self,kind,p):
        self.saved.append((kind,p));return p
    def log(self,*args):self.logs.append(args)

class RuntimeAudioTest(unittest.TestCase):
    def setUp(self):
        self.s=Store();self.c=Cognition(type("R",(),{"store":self.s})())
        self.e={"source_ref":{"source_id":"fixture"},"event_id":"event1","brain_generation_id":"gen1"}
        self.frame=[{"start_ms":0,"end_ms":20,"rms":0.1,"spectral_flux":0.4}]
    def test_real_consumer_packet_and_telemetry(self):
        p=self.c.audio_percept(self.e,self.frame,consent=True,capture_id="fixture",sample_rate_hz=16000)
        self.assertEqual(p["modality"],"audio")
        self.assertEqual(self.s.saved[0][0],"PerceptPacket")
        self.assertEqual(self.s.logs[0][0],"audio_percept_observed")
        self.assertFalse(p["android_capture_verified"])
    def test_no_consent_no_packet(self):
        with self.assertRaises(PermissionError):
            self.c.audio_percept(self.e,self.frame,consent=False,capture_id="fixture",sample_rate_hz=16000)
        self.assertEqual(self.s.saved,[])
    def test_revoked_source_no_packet(self):
        self.e["source_ref"]={"source_id":"revoked"}
        with self.assertRaises(ValueError):
            self.c.audio_percept(self.e,self.frame,consent=True,capture_id="fixture",sample_rate_hz=16000)
        self.assertEqual(self.s.saved,[])
if __name__=="__main__":unittest.main()
