import unittest
from v13.audio_percept import audio_observation,persist_audio_percept
from v13.contracts import validate
REF={"source_id":"s1","sha256":"abc","char_start":0,"char_end":0,"modality":"audio"}
class AudioContract(unittest.TestCase):
    def opts(self):return dict(start_ms=10,end_ms=40,features={"rms":.2,"pitch_hz":180,"noise_probability":.3},consent=True)
    def test_nonverbal_provisional(self):
        x=audio_observation(REF,**self.opts())
        self.assertEqual(x["teacher"],None)
        self.assertEqual(x["finality"],"PROVISIONAL")
        self.assertEqual(x["truth_authority"],0)
    def test_consent_and_timestamps(self):
        for change,exc in (({"consent":False},PermissionError),({"end_ms":10},ValueError),({"start_ms":float("nan")},ValueError),({"features":{"rms":1.2}},ValueError)):
            with self.assertRaises(exc):audio_observation(REF,**(self.opts()|change))
    def test_teacher_source_binding(self):
        with self.assertRaises(ValueError):audio_observation(REF,**(self.opts()|{"teacher":{"kind":"ASR","text":"hi","source_ref":{}}}))
    def test_store_consumer(self):
        class Store:
            def add_packet(self,kind,p):
                validate(kind,p);self.kind=kind;self.packet=p;return p
        e={"source_ref":REF,"event_id":"e1","brain_generation_id":"g1"}
        s=Store();p=persist_audio_percept(s,e,REF,**self.opts())
        self.assertEqual(s.kind,"PerceptPacket")
        self.assertEqual(p["acoustic_features"]["rms"],.2)
        self.assertEqual(p["segments"],[])
    def test_cross_event_rejected(self):
        with self.assertRaises(ValueError):
            persist_audio_percept(None,{"source_ref":REF|{"source_id":"other"},"event_id":"e","brain_generation_id":"g"},REF,**self.opts())
if __name__=="__main__":unittest.main()
