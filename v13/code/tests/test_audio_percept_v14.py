import unittest
from v13.audio_percept_v14 import AudioFrame, publish_audio_frame

class Bus:
    def __init__(self): self.calls=[]
    def publish(self,*a,**kw):
        self.calls.append((a,kw))
        return {"status":"PUBLISHED"}

class TimedAudioTest(unittest.TestCase):
    def test_valid_nonverbal_provisional(self):
        bus=Bus()
        f=AudioFrame("local-opaque",100,220,.12,non_speech="laughter",consent=True)
        self.assertEqual(publish_audio_frame(bus,{"event_id":"e","brain_generation_id":"g"},f)["status"],"PUBLISHED")
        self.assertIn("laughter",bus.calls[0][1]["summary"])
        self.assertIn("provisional",bus.calls[0][1]["summary"])
        self.assertEqual(bus.calls[0][1]["authority"],"CONTROL_ONLY")
        self.assertNotIn("source_refs",bus.calls[0][1])
    def test_consent(self):
        bus=Bus()
        with self.assertRaises(PermissionError): publish_audio_frame(bus,{},AudioFrame("x",0,10,.1))
        self.assertFalse(bus.calls)
    def test_invalid_intervals_and_features(self):
        for f in (AudioFrame("x",10,10,.1,consent=True),
                  AudioFrame("x",0,40000,.1,consent=True),
                  AudioFrame("x",0,10,float("nan"),consent=True),
                  AudioFrame("x",0,10,.1,voiced_probability=2,consent=True),
                  AudioFrame("x",0,10,.1,speaker_label="secret\nline",consent=True)):
            with self.subTest(f=f),self.assertRaises(ValueError): f.validate()
    def test_final_feature(self):
        bus=Bus()
        publish_audio_frame(bus,{},AudioFrame("x",0,10,.1,pitch_hz=140,final=True,consent=True))
        self.assertIn("provenance=final",bus.calls[0][1]["summary"])

if __name__=="__main__": unittest.main()
