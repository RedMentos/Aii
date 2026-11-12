import unittest, hashlib, json
from v13.a5_audio_integrity import checked_audio_integrity_view
from v13.a3_runtime_adapter import FeatureObservation

class Store:
    def __init__(self, raw): self.raw=raw; self.revoked=False
    def read_source(self, ref):
        if self.revoked: raise PermissionError('revoked')
        if hashlib.sha256(self.raw.encode()).hexdigest()!=ref['sha256']: raise ValueError('hash mismatch')
        return self.raw

def fixture():
    raw=json.dumps({'features':[0.3,0.1],'final':True,'start_ms':0,'end_ms':20,'sample_rate_hz':16000,'acoustic':{'rms':0.3,'pitch_hz':0,'speech_probability':0}},sort_keys=True)
    sha=hashlib.sha256(raw.encode()).hexdigest()
    ref={'source_id':'s1','sha256':sha,'char_start':0,'char_end':len(raw),'modality':'text'}
    obs=FeatureObservation('s1','synthetic_audio',(0.3,0.1),True,'')
    feature_sha=hashlib.sha256(obs.canonical_bytes()).hexdigest()
    candidate={'schema':'v13.a5.audio.observation_candidate.v1','canonical_a5':False,'status':'SHADOW','authority':'observation_only','android_action_allowed':False,'runtime_consumer':'NOT_CONNECTED','transcript':None,'source':{'id':'s1','store_sha256':sha,'feature_sha256':feature_sha,'final':True},'time':{'start_ms':0,'end_ms':20,'sample_rate_hz':16000},'raw_ear':{'rms':0.3},'a3':{'embedding':[0.2]},'a4':{'score':0.3}}
    return Store(raw),ref,candidate

class Tests(unittest.TestCase):
    def test_valid(self):
        s,r,c=fixture(); self.assertEqual(checked_audio_integrity_view(s,c,r)['feature_sha256'],c['source']['feature_sha256'])
    def test_forged_feature_digest(self):
        s,r,c=fixture(); c['source']['feature_sha256']='a'*64
        with self.assertRaises(ValueError): checked_audio_integrity_view(s,c,r)
    def test_nan_embedding(self):
        s,r,c=fixture(); c['a3']['embedding']=[float('nan')]
        with self.assertRaises(ValueError): checked_audio_integrity_view(s,c,r)
    def test_bad_salience(self):
        s,r,c=fixture(); c['a4']['score']=2
        with self.assertRaises(ValueError): checked_audio_integrity_view(s,c,r)
    def test_revoked(self):
        s,r,c=fixture(); s.revoked=True
        with self.assertRaises(PermissionError): checked_audio_integrity_view(s,c,r)
    def test_rms_inconsistent(self):
        s,r,c=fixture(); d=json.loads(s.raw); d['features'][0]=0.2; s.raw=json.dumps(d,sort_keys=True); r['sha256']=hashlib.sha256(s.raw.encode()).hexdigest(); r['char_end']=len(s.raw); c['source']['store_sha256']=r['sha256']
        with self.assertRaises(ValueError): checked_audio_integrity_view(s,c,r)

if __name__=='__main__': unittest.main()
