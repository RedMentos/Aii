import unittest
from copy import deepcopy
from v13.audio_percept_bridge import acoustic_percept, admit_acoustic_packets

def fixture(final=True):
    return {"schema":"v13.a5.raw_ear/1",
      "source_ref":{"source_id":"fixture","consent_id":"synthetic","sha256":"a"*64,"start_ms":0,"end_ms":10},
      "provenance":"RAW_PCM_OBSERVATION","learning_eligible":False,
      "status":"FINAL" if final else "PROVISIONAL","teacher_asr":None,"speaker_identity":None,
      "acoustic_features":{"rms":0.1,"peak":0.2,"zero_crossing_rate":0.3,
                           "silence_candidate":False,"clipped":False}}

class TestAudioBridge(unittest.TestCase):
    def test_final_admitted(self):
        a=admit_acoustic_packets([fixture()],512)
        self.assertEqual(len(a.selected),1)
        self.assertNotIn("synthetic",a.selected[0].summary)
    def test_provisional_omitted(self):
        self.assertEqual(len(admit_acoustic_packets([fixture(False)],512).selected),0)
    def test_budget(self):
        self.assertEqual(len(admit_acoustic_packets([fixture()],0).selected),0)
    def test_consent(self):
        p=fixture();p["source_ref"]["consent_id"]=""
        with self.assertRaises(PermissionError):acoustic_percept(p)
    def test_nonfinite(self):
        p=fixture();p["acoustic_features"]["rms"]=float("nan")
        with self.assertRaises(ValueError):acoustic_percept(p)
    def test_untrusted_teacher(self):
        p=fixture();p["teacher_asr"]="hello"
        with self.assertRaises(ValueError):acoustic_percept(p)
    def test_learning_authority(self):
        p=fixture();p["learning_eligible"]=True
        with self.assertRaises(ValueError):acoustic_percept(p)
    def test_long_source_id_consumer_boundary(self):
        p=fixture();p['source_ref']['source_id']='s'*128
        admitted=admit_acoustic_packets([p],512)
        self.assertEqual(len(admitted.selected),1)
        self.assertLessEqual(len(admitted.selected[0].source_id),128)
    def test_consent_and_timing_bind_identity(self):
        p=fixture();q=deepcopy(p);q['source_ref']['consent_id']='different'
        self.assertNotEqual(acoustic_percept(p).source_id,acoustic_percept(q).source_id)
        q=deepcopy(p);q['source_ref']['start_ms']=1
        self.assertNotEqual(acoustic_percept(p).source_id,acoustic_percept(q).source_id)
    def test_frame_identity(self):
        p=fixture();q=deepcopy(p);q["source_ref"]["sha256"]="b"*64
        self.assertNotEqual(acoustic_percept(p).source_id,acoustic_percept(q).source_id)
