"""Run163 adversarial, source-bound read-only FP32 audit tests."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.body_fp32_export_verify_run163 import verify, GATES


def u32(x): return struct.pack('<I', x)
def u64(x): return struct.pack('<Q', x)
def s(x):
    b = x.encode()
    return u64(len(b)) + b


def gguf(values=None, overlap=False):
    if values is None: values = [1., -0., 3., 4.]
    raw = np.asarray(values, dtype='<f4').tobytes()
    count = 2 if overlap else 1
    header = b'GGUF' + u32(3) + u64(count) + u64(0)
    header += s('norm.weight') + u32(1) + u64(4) + u32(0) + u64(0)
    if overlap:
        header += s('copy.weight') + u32(1) + u64(4) + u32(0) + u64(0)
    header += b'\0' * (-len(header) % 32)
    return header + raw, len(header), raw


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.model = self.root / 'model.gguf'
        self.master = self.root / 'master.npz'
        self.report = self.root / 'report.json'
        b, pos, raw = gguf()
        self.model.write_bytes(b)
        self.sha = hashlib.sha256(b).hexdigest()
        self.arr = np.frombuffer(raw, dtype='<f4').copy()
        self.r = {'schema': 'V13_RUN162_FP32_SLICE_EXPORT_V1',
                  'registered_model_sha256': self.sha, 'full_model_sha256_verified': True,
                  'master_candidate_sha256': '', 'master_candidate_bytes': 0,
                  'body_training_authority': 0, 'train_master_authority': 0,
                  'gates': GATES,
                  'selected_tensors': [{'name': 'norm.weight', 'shape': [4], 'dtype': 'float32',
                                        'bytes': 16, 'offset_in_gguf': pos,
                                        'sha256': hashlib.sha256(raw).hexdigest()}]}
        self.save()

    def save(self):
        with self.master.open('wb') as f: np.savez(f, **{'norm.weight': self.arr})
        self.r['master_candidate_sha256'] = hashlib.sha256(self.master.read_bytes()).hexdigest()
        self.r['master_candidate_bytes'] = self.master.stat().st_size
        self.report.write_text(json.dumps(self.r))

    def test_exact_source_and_negative_gates(self):
        r = verify(self.model, self.master, self.report, self.sha)
        self.assertTrue(r['selected_bytes_exact']); self.assertEqual(r['gates'], GATES)
        self.assertEqual(r['body_training_authority'], 0)

    def test_signed_zero_counterexample_to_numpy_array_equal(self):
        changed = self.arr.copy(); changed[1] = 0.
        self.assertTrue(np.array_equal(changed, self.arr))
        self.arr = changed; self.save()
        with self.assertRaisesRegex(ValueError, 'npz_source_bytes_mismatch'):
            verify(self.model, self.master, self.report, self.sha)

    def test_wrong_external_model_sha(self):
        with self.assertRaisesRegex(ValueError, 'external_model_sha_mismatch'):
            verify(self.model, self.master, self.report, '0' * 64)

    def test_tampered_npz_digest(self):
        self.master.write_bytes(self.master.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'master_digest_mismatch'):
            verify(self.model, self.master, self.report, self.sha)

    def test_forged_tensor_digest(self):
        self.r['selected_tensors'][0]['sha256'] = '0' * 64
        self.report.write_text(json.dumps(self.r))
        with self.assertRaisesRegex(ValueError, 'source_tensor_digest'):
            verify(self.model, self.master, self.report, self.sha)

    def test_source_span_overlap(self):
        b, pos, raw = gguf(overlap=True)
        self.model.write_bytes(b); self.sha = hashlib.sha256(b).hexdigest()
        self.r['registered_model_sha256'] = self.sha
        self.r['selected_tensors'][0]['offset_in_gguf'] = pos
        self.r['selected_tensors'].append(dict(self.r['selected_tensors'][0], name='copy.weight'))
        self.report.write_text(json.dumps(self.r))
        with self.assertRaisesRegex(ValueError, 'selected_source_spans_overlap'):
            verify(self.model, self.master, self.report, self.sha)

    def test_extra_npz_entry(self):
        with zipfile.ZipFile(self.master, 'a') as z: z.writestr('extra.npy', b'junk')
        self.r['master_candidate_sha256'] = hashlib.sha256(self.master.read_bytes()).hexdigest()
        self.r['master_candidate_bytes'] = self.master.stat().st_size
        self.report.write_text(json.dumps(self.r))
        with self.assertRaisesRegex(ValueError, 'npz_entries_mismatch'):
            verify(self.model, self.master, self.report, self.sha)

    def test_symlink_master_rejected(self):
        alias = self.root / 'alias.npz'; alias.symlink_to(self.master)
        with self.assertRaisesRegex(ValueError, 'regular_nonsymlink_files_required'):
            verify(self.model, alias, self.report, self.sha)

    def test_manifest_offset_mismatch(self):
        self.r['selected_tensors'][0]['offset_in_gguf'] += 32
        self.report.write_text(json.dumps(self.r))
        with self.assertRaisesRegex(ValueError, 'source_manifest_mismatch'):
            verify(self.model, self.master, self.report, self.sha)

    def test_forged_authority_rejected(self):
        self.r['body_training_authority'] = 1
        self.report.write_text(json.dumps(self.r))
        with self.assertRaisesRegex(ValueError, 'authority_or_gates'):
            verify(self.model, self.master, self.report, self.sha)

    def test_quantized_claim_rejected(self):
        b = bytearray(self.model.read_bytes())
        # Rebuild with type Q4_0; original F32 bytes cannot become trainable.
        h = b'GGUF' + u32(3) + u64(1) + u64(0) + s('norm.weight') + u32(1) + u64(4) + u32(2) + u64(0)
        h += b'\0' * (-len(h) % 32)
        self.model.write_bytes(h + self.arr.tobytes())
        self.sha = hashlib.sha256(self.model.read_bytes()).hexdigest()
        self.r['registered_model_sha256'] = self.sha
        self.report.write_text(json.dumps(self.r))
        with self.assertRaisesRegex(ValueError, 'source_tensor_not_f32_vector'):
            verify(self.model, self.master, self.report, self.sha)

if __name__ == '__main__': unittest.main()
