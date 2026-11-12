import unittest, json, hashlib
from v13.a5_audio_source_gate import checked_audio_view

class Store:
    def __init__(self, raw): self.raw=raw;self.revoked=False;self.calls=0
    def read_source(self,ref):
        self.calls+=1
        if self.revoked: raise PermissionError('revoked')
        if hashlib.sha256(self.raw.encode()).hexdigest()!=ref['sha256']:raise ValueError('hash mismatch')
        return self.raw

def fixture():
    raw=json.dumps({'features':[0.3,0.1],'final':True,'start_ms':0,'end_ms':20,'sample_rate_hz':16000,'acoustic':{'rms':0.3,'pitch_hz':0,'speech_probability':0}},sort_keys=True)
    sha=hashlib.sha256(raw.encode()).hexdigest()
    ref={'source_id':'s1','sha256':sha,'char_start':0,'char_end':len(raw),'modality':'text'}
    candidate={'schema':'v13.a5.audio.observation_candidate.v1','canonical_a5':False,'status':'SHADOW','authority':'observation_only','android_action_allowed':False,'runtime_consumer':'NOT_CONNECTED','transcript':None,'source':{'id':'s1','store_sha256':sha,'feature_sha256':'a'*64,'final':True},'time':{'start_ms':0,'end_ms':20,'sample_rate_hz':16000},'raw_ear':{'rms':0.3},'a3':{'embedding':[0.2]},'a4':{'score':0.3}}
    return Store(raw),ref,candidate

class Tests(unittest.TestCase):
    def test_valid(self):
        s,r,c=fixture();x=checked_audio_view(s,c,r);self.assertFalse(x['body_inference_executed']);self.assertEqual(s.calls,2)
    def test_revoked(self):
        s,r,c=fixture();s.revoked=True
        with self.assertRaises(PermissionError):checked_audio_view(s,c,r)
    def test_forged_authority(self):
        s,r,c=fixture();c['android_action_allowed']=True
        with self.assertRaises(PermissionError):checked_audio_view(s,c,r)
    def test_mismatch(self):
        s,r,c=fixture();c['time']['end_ms']=30
        with self.assertRaises(ValueError):checked_audio_view(s,c,r)
    def test_changed_source(self):
        s,r,c=fixture();s.raw+=' '
        with self.assertRaises(ValueError):checked_audio_view(s,c,r)
if __name__=='__main__':unittest.main()
