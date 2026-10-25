"""Run160 synthetic GGUF v3 metadata and train-port claim guard tests."""
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from body_gguf_dtype_audit_run160 import parse,audit,GATES


def u32(n):return struct.pack('<I',n)
def u64(n):return struct.pack('<Q',n)
def s(x):
    b=x.encode();return u64(len(b))+b

def fixture(tensors=(('norm.weight',0),('block.weight',2)),kv=()):
    b=b'GGUF'+u32(3)+u64(len(tensors))+u64(len(kv))
    for key,kind,payload in kv:b+=s(key)+u32(kind)+payload
    for name,dtype in tensors:b+=s(name)+u32(1)+u64(32)+u32(dtype)+u64(0)
    return b

class GGUFPortAudit(unittest.TestCase):
    def test_fp32_claim_valid_but_no_authority(self):
        r=audit(fixture(),['norm.weight'])
        self.assertTrue(r['fp32_claims_valid'])
        self.assertEqual(r['body_training_authority'],0)
        self.assertFalse(r['full_model_sha256_verified'])

    def test_quantized_claim_rejected(self):
        r=audit(fixture(),['block.weight'])
        self.assertFalse(r['fp32_claims_valid'])
        self.assertEqual(r['quantized_claims'],['block.weight'])

    def test_unknown_claim_rejected(self):
        r=audit(fixture(),['nonexistent'])
        self.assertFalse(r['fp32_claims_valid'])
        self.assertEqual(r['missing_claims'],['nonexistent'])

    def test_truncated_rejected(self):
        with self.assertRaisesRegex(ValueError,'truncated'):parse(fixture()[:-1])

    def test_duplicate_tensor_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):parse(fixture((('a',0),('a',2))))

    def test_invalid_version_rejected(self):
        b=bytearray(fixture());b[4:8]=u32(2)
        with self.assertRaisesRegex(ValueError,'version'):parse(bytes(b))

    def test_oversized_metadata_rejected(self):
        b=fixture(kv=(('oversize',8,u64(33*1024*1024)),))
        with self.assertRaisesRegex(ValueError,'string_bounds'):parse(b)

    def test_negative_gates(self):
        r=audit(fixture());self.assertEqual(r['gates'],GATES)
        self.assertEqual(r['gate'],'UNVERIFIED')

if __name__=='__main__':unittest.main()
