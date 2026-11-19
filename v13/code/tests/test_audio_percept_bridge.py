import unittest
from dataclasses import replace
from v13.audio_percept_bridge import AudioObservation, make_a5_audio_packet, publish_audio_percept

class Bus:
    def __init__(self): self.calls=[]
    def publish(self,*args,**kwargs):
        self.calls.append((args,kwargs))
        return {"status":"PUBLISHED"}

class TestAudio(unittest.TestCase):
    def setUp(self):
        self.o=AudioObservation("consented-stream",10,90,.25,170.,.8,True,"LAUGHTER","PROVISIONAL",True)
        self.e={"event_id":"e1","brain_generation_id":"g1"}
    def test_a5(self):
        p=make_a5_audio_packet(self.o,self.e)
        self.assertEqual((p["start_ms"],p["end_ms"],p["non_speech"],p["phase"]),(10,90,"LAUGHTER","PROVISIONAL"))
        self.assertIsNone(p["asr_text"])
    def test_bus(self):
        b=Bus(); p,r=publish_audio_percept(b,self.o,self.e)
        self.assertEqual(r["status"],"PUBLISHED")
        self.assertEqual(b.calls[0][0][1:3],("A_PERCEPTION","CONTROL"))
        self.assertEqual(b.calls[0][1]["authority"],"CONTROL_ONLY")
    def test_consent(self):
        with self.assertRaises(PermissionError): publish_audio_percept(Bus(),replace(self.o,consent=False),self.e)
    def test_time(self):
        with self.assertRaises(ValueError): make_a5_audio_packet(replace(self.o,end_ms=10),self.e)
    def test_nan(self):
        with self.assertRaises(ValueError): make_a5_audio_packet(replace(self.o,energy_rms=float("nan")),self.e)
    def test_generation(self):
        with self.assertRaises(ValueError): make_a5_audio_packet(self.o,{"event_id":"e1"})
    def test_final(self):
        self.assertEqual(make_a5_audio_packet(replace(self.o,phase="FINAL"),self.e)["phase"],"FINAL")
    def test_window(self):
        with self.assertRaises(ValueError): make_a5_audio_packet(replace(self.o,end_ms=31000),self.e)
