"""Run180 independent raw evidence audit software tests, no model."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/run180_b2_gist_audit.py'
spec=importlib.util.spec_from_file_location('run180_audit',SCRIPT)
audit_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit_module)


class RawAuditTests(unittest.TestCase):
    def fixture(self,root):
        root=Path(root);source='abc'
        v=np.stack([np.full(1024,i+1,dtype=np.float64) for i in range(3)])
        np.savez_compressed(root/'raw-token-vectors.npz',token_ids=np.array([1,2,3],dtype=np.int32),vectors=v)
        (root/'native-token-pieces.json').write_text(json.dumps([
            {'id':1,'piece':'a'},{'id':2,'piece':'b'},{'id':3,'piece':'c'}])+'\n')
        slots=[]
        for a,b,cs,ce in ((0,2,0,2),(2,3,2,3)):
            slots.append({'native_tokens':[a,b],'source_ref':{'char_start':cs,'char_end':ce},
                          'text':source[cs:ce],
                          'vector_sha256':hashlib.sha256(np.asarray(v[a:b].mean(axis=0),dtype='<f4').tobytes()).hexdigest()})
        plan={'dim':1024,'tap_id':'qwen35.result_norm.final.v1','lossless':True,
              'authority':'SHADOW','receiver_read_authority':0,'receiver_injection_authority':0,
              'body_learning_authority':0,'slots':slots}
        (root/'gist-plan.json').write_text(json.dumps(plan)+'\n')
        m={'schema':'V13_RUN180_B2_GIST_NATIVE_RAW_V1','status':'NATIVE_READONLY_GIST_CONSUMER_PASS',
           'model_sha256':audit_module.MODEL_SHA,'embedding_dim':1024,'tap_id':'qwen35.result_norm.final.v1',
           'source_text':source,'token_count':3,'slot_count':2,
           'step2_promoted':False,'b3_promoted':False,'body_learning':False,'redmi_proven':False,
           'full_v13_proven':False,'files_sha256':{n:audit_module.digest(root/n) for n in
                ('raw-token-vectors.npz','native-token-pieces.json','gist-plan.json')}}
        (root/'manifest.json').write_text(json.dumps(m)+'\n')
        return m

    def test_valid_source_bound_synthetic(self):
        with tempfile.TemporaryDirectory() as d:
            self.fixture(d)
            self.assertEqual(audit_module.audit(d)['status'],'INDEPENDENT_RAW_AUDIT_PASS')

    def test_raw_vector_tamper_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self.fixture(d)
            p=Path(d)/'raw-token-vectors.npz';p.write_bytes(p.read_bytes()+b'X')
            with self.assertRaisesRegex(ValueError,'raw file hash mismatch'):
                audit_module.audit(d)

    def test_plan_authority_tamper_refused_even_with_rehashed_file(self):
        with tempfile.TemporaryDirectory() as d:
            m=self.fixture(d);p=Path(d)/'gist-plan.json';plan=json.loads(p.read_text())
            plan['receiver_injection_authority']=1;p.write_text(json.dumps(plan)+'\n')
            m['files_sha256'][p.name]=audit_module.digest(p)
            (Path(d)/'manifest.json').write_text(json.dumps(m)+'\n')
            with self.assertRaisesRegex(ValueError,'unauthorized authority'):
                audit_module.audit(d)

    def test_slot_vector_hash_tamper_refused(self):
        with tempfile.TemporaryDirectory() as d:
            m=self.fixture(d);p=Path(d)/'gist-plan.json';plan=json.loads(p.read_text())
            plan['slots'][0]['vector_sha256']='0'*64;p.write_text(json.dumps(plan)+'\n')
            m['files_sha256'][p.name]=audit_module.digest(p)
            (Path(d)/'manifest.json').write_text(json.dumps(m)+'\n')
            with self.assertRaisesRegex(ValueError,'slot vector hash mismatch'):
                audit_module.audit(d)


if __name__=='__main__':unittest.main()
