"""Run162 synthetic GGUF FP32 export integrity tests, no model training."""
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from body_fp32_master_export_run162 import export,GATES
from body_gguf_dtype_audit_run160 import parse

def u32(x):return struct.pack('<I',x)
def u64(x):return struct.pack('<Q',x)
def s(x):
    b=x.encode();return u64(len(b))+b

def gguf(dtype=0,offset=0,payload=None):
    if payload is None:payload=np.array([1,2,3,4],dtype='<f4').tobytes()
    header=b'GGUF'+u32(3)+u64(1)+u64(0)+s('norm.weight')+u32(1)+u64(4)+u32(dtype)+u64(offset)
    header+=b'\0'*((-len(header))%32)
    return header+payload

class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.model=self.root/'model.gguf';self.out=self.root/'master.npz'
        self.model.write_bytes(gguf());self.sha=hashlib.sha256(self.model.read_bytes()).hexdigest()

    def test_roundtrip_and_no_authority(self):
        r=export(self.model,self.sha,['norm.weight'],self.out)
        self.assertTrue(r['model_file_unchanged'])
        self.assertEqual(r['body_training_authority'],0)
        self.assertEqual(r['gates'],GATES)
        with np.load(self.out,allow_pickle=False) as z:
            self.assertEqual(z['norm.weight'].tolist(),[1,2,3,4])

    def test_hash_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,'full_model_hash_mismatch'):
            export(self.model,'0'*64,['norm.weight'],self.out)
        self.assertFalse(self.out.exists())

    def test_quantized_tensor_rejected(self):
        self.model.write_bytes(gguf(dtype=2));sha=hashlib.sha256(self.model.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'not_fp32'):
            export(self.model,sha,['norm.weight'],self.out)

    def test_nonvector_slice_rejected(self):
        b=gguf()
        # Change tensor dimensions from one to two; rebuild the bounded fixture.
        h=b'GGUF'+u32(3)+u64(1)+u64(0)+s('norm.weight')+u32(2)+u64(2)+u64(2)+u32(0)+u64(0)
        h+=b'\0'*((-len(h))%32)
        self.model.write_bytes(h+np.array([1,2,3,4],dtype='<f4').tobytes())
        sha=hashlib.sha256(self.model.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'nonvector_slice'):
            export(self.model,sha,['norm.weight'],self.out)

    def test_missing_tensor_rejected(self):
        with self.assertRaisesRegex(ValueError,'missing_tensor'):
            export(self.model,self.sha,['unknown'],self.out)

    def test_out_of_file_rejected(self):
        self.model.write_bytes(gguf(offset=1024));sha=hashlib.sha256(self.model.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'tensor_out_of_file'):
            export(self.model,sha,['norm.weight'],self.out)

    def test_nonfinite_rejected(self):
        self.model.write_bytes(gguf(payload=np.array([1,float('nan'),3,4],dtype='<f4').tobytes()))
        sha=hashlib.sha256(self.model.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'nonfinite_master'):
            export(self.model,sha,['norm.weight'],self.out)

    def test_duplicate_selection_rejected(self):
        with self.assertRaisesRegex(ValueError,'selection'):
            export(self.model,self.sha,['norm.weight','norm.weight'],self.out)

    def test_existing_master_not_overwritten(self):
        self.out.write_bytes(b'original')
        with self.assertRaises(FileExistsError):export(self.model,self.sha,['norm.weight'],self.out)
        self.assertEqual(self.out.read_bytes(),b'original')

    def test_parser_layout_alignment(self):
        r=parse(gguf());self.assertEqual(r['alignment'],32)
        self.assertEqual(r['tensor_data_start']%32,0)

if __name__=='__main__':unittest.main()
