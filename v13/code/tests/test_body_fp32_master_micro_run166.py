"""Run166 isolated FP32 micro tests; only synthetic GGUF fixture, no model weights."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.body_fp32_master_export_run162 import export
from scripts.body_fp32_master_micro_run166 import micro,GATES


def u32(x):return struct.pack('<I',x)
def u64(x):return struct.pack('<Q',x)
def s(x):
    b=x.encode();return u64(len(b))+b

class MicroTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.model=self.root/'source.gguf';self.master=self.root/'input-master.npz'
        self.report=self.root/'report.json';self.out=self.root/'private-candidate.npz'
        values=np.array([.7,1.1,1.0,-.3],dtype='<f4')
        h=b'GGUF'+u32(3)+u64(1)+u64(0)+s('norm.weight')+u32(1)+u64(4)+u32(0)+u64(0)
        h+=b'\0'*(-len(h)%32)
        self.model.write_bytes(h+values.tobytes())
        self.sha=hashlib.sha256(self.model.read_bytes()).hexdigest()
        self.r=export(self.model,self.sha,['norm.weight'],self.master)
        self.report.write_text(json.dumps(self.r))

    def test_autograd_ema_persist_rollback_no_authority(self):
        r=micro(self.model,self.master,self.report,self.sha,self.out)
        self.assertTrue(r['gradients_finite_nonzero'])
        self.assertTrue(r['rollback_exact_baseline'])
        self.assertTrue(r['exclusive_persist_reload'])
        self.assertTrue(r['inference_gguf_unchanged'])
        self.assertEqual(r['gates'],GATES)
        self.assertEqual(r['body_training_authority'],0)
        self.assertLess(r['applied_update_l2'],.2+1e-5)
        with np.load(self.out,allow_pickle=False) as z:
            original=z['baseline__norm.weight'];changed=z['updated__norm.weight'];slow=z['ema__norm.weight']
            self.assertTrue(np.any(changed!=original))
            self.assertTrue(np.all(np.abs(slow-original)<=np.abs(changed-original)+1e-6))

    def test_bad_model_sha_rejected_before_output(self):
        with self.assertRaisesRegex(ValueError,'external_model_sha_mismatch'):
            micro(self.model,self.master,self.report,'0'*64,self.out)
        self.assertFalse(self.out.exists())

    def test_existing_candidate_not_overwritten(self):
        self.out.write_bytes(b'prior-private-checkpoint')
        with self.assertRaises(FileExistsError):micro(self.model,self.master,self.report,self.sha,self.out)
        self.assertEqual(self.out.read_bytes(),b'prior-private-checkpoint')

    def test_input_master_tamper_rejected(self):
        self.master.write_bytes(self.master.read_bytes()+b'tamper')
        with self.assertRaisesRegex(ValueError,'master_digest_mismatch'):
            micro(self.model,self.master,self.report,self.sha,self.out)
        self.assertFalse(self.out.exists())

    def test_report_authority_forgery_rejected(self):
        self.r['body_training_authority']=1;self.report.write_text(json.dumps(self.r))
        with self.assertRaisesRegex(ValueError,'authority_or_gates'):
            micro(self.model,self.master,self.report,self.sha,self.out)
        self.assertFalse(self.out.exists())

if __name__=='__main__':unittest.main()
