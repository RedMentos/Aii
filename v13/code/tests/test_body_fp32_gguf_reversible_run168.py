"""Run168 reversible binary patch tests, only disposable synthetic GGUF."""
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
from scripts.body_fp32_master_micro_run166 import micro
from scripts.body_fp32_gguf_reversible_run168 import patch_rollback,GATES


def u32(x):return struct.pack('<I',x)
def u64(x):return struct.pack('<Q',x)
def s(x):
    b=x.encode();return u64(len(b))+b

class ReversibleTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name);self.model=self.root/'model.gguf'
        self.master=self.root/'master.npz';self.report=self.root/'report.json'
        self.micro=self.root/'micro.npz';self.micro_report=self.root/'micro-report.json'
        self.out=self.root/'patched.gguf'
        h=b'GGUF'+u32(3)+u64(2)+u64(0)
        for i in range(2):h+=s(f'norm.{i}.weight')+u32(1)+u64(4)+u32(0)+u64(i*32)
        h+=b'\0'*(-len(h)%32)
        data=b''.join(np.array([1.+i,2.+i,3.+i,4.+i],dtype='<f4').tobytes()+b'\0'*16 for i in range(2))
        self.model.write_bytes(h+data)
        self.sha=hashlib.sha256(self.model.read_bytes()).hexdigest()
        r=export(self.model,self.sha,['norm.0.weight','norm.1.weight'],self.master)
        self.report.write_text(json.dumps(r))
        m=micro(self.model,self.master,self.report,self.sha,self.micro)
        self.micro_report.write_text(json.dumps(m))

    def run_patch(self):
        return patch_rollback(self.model,self.master,self.report,self.micro,
                              self.micro_report,self.sha,self.out)

    def test_private_patch_only_f32_and_exact_rollback(self):
        r=self.run_patch()
        self.assertNotEqual(r['private_patched_sha256_before_rollback'],self.sha)
        self.assertEqual(r['private_restored_sha256'],self.sha)
        self.assertEqual(self.out.read_bytes(),self.model.read_bytes())
        self.assertEqual(r['selected_spans'],2)
        self.assertEqual(r['quantized_tensors_touched'],0)
        self.assertTrue(r['unselected_bytes_identical'])
        self.assertEqual(r['body_training_authority'],0)
        self.assertEqual(r['gates'],GATES)

    def test_existing_output_not_overwritten(self):
        self.out.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):self.run_patch()
        self.assertEqual(self.out.read_bytes(),b'keep')

    def test_micro_digest_tamper_fails_before_output(self):
        self.micro.write_bytes(self.micro.read_bytes()+b'tamper')
        with self.assertRaisesRegex(ValueError,'micro_binding_or_authority'):self.run_patch()
        self.assertFalse(self.out.exists())

    def test_forged_authority_fails_before_output(self):
        m=json.loads(self.micro_report.read_text());m['body_training_authority']=1
        self.micro_report.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'micro_binding_or_authority'):self.run_patch()
        self.assertFalse(self.out.exists())

    def test_wrong_source_sha_fails_before_output(self):
        with self.assertRaisesRegex(ValueError,'external_model_sha_mismatch'):
            patch_rollback(self.model,self.master,self.report,self.micro,self.micro_report,'0'*64,self.out)
        self.assertFalse(self.out.exists())

    def test_quantized_alias_of_f32_span_rejected(self):
        # Malformed GGUF: a Q4_0 tensor shares the selected F32 vector offset.
        # Run162/163 only inspect selected F32; Run168 must inspect ALL spans.
        h=b'GGUF'+u32(3)+u64(2)+u64(0)
        h+=s('quant.weight')+u32(1)+u64(32)+u32(2)+u64(0)
        h+=s('norm.0.weight')+u32(1)+u64(4)+u32(0)+u64(0)
        h+=b'\0'*(-len(h)%32)
        self.model.write_bytes(h+np.array([1.,2.,3.,4.],dtype='<f4').tobytes()+b'\0'*16)
        self.sha=hashlib.sha256(self.model.read_bytes()).hexdigest()
        self.master.unlink();self.micro.unlink()
        r=export(self.model,self.sha,['norm.0.weight'],self.master)
        self.report.write_text(json.dumps(r))
        m=micro(self.model,self.master,self.report,self.sha,self.micro)
        self.micro_report.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'ggml_tensor_span_overlap'):
            self.run_patch()
        self.assertFalse(self.out.exists())

if __name__=='__main__':unittest.main()
