"""P2 QAD FP32 value audit source-only tests; no model downloads."""
import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'p2_qad_fp32_value_audit.py'
spec = importlib.util.spec_from_file_location('p2_qad_fp32', SCRIPT)
import sys
sys.path.insert(0, str(SCRIPT.parent))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ValueAuditTests(unittest.TestCase):
    def test_identical_values_not_parity_promotion(self):
        x = np.array([1., 2., 3.], dtype=np.float32)
        result = audit.value_stats(x, x)
        self.assertEqual(result['cosine'], 1.)
        self.assertEqual(result['normalized_rmse'], 0.)

    def test_orthogonal_values_descriptive(self):
        result = audit.value_stats([1., 0.], [0., 1.], block=1)
        self.assertEqual(result['cosine'], 0.)
        self.assertGreater(result['normalized_rmse'], 0.)

    def test_shape_count_mismatch_red(self):
        with self.assertRaisesRegex(ValueError, 'count mismatch'):
            audit.value_stats([1., 2.], [1.])

    def test_nonfinite_values_red(self):
        with self.assertRaisesRegex(ValueError, 'nonfinite'):
            audit.value_stats([float('nan')], [1.])

    def test_zero_reference_finite(self):
        result = audit.value_stats([0., 0.], [0., 0.])
        self.assertEqual(result['cosine'], 1.)
        self.assertEqual(result['normalized_rmse'], 0.)

    def test_f32_offsets_header_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'model.safetensors'
            h = json.dumps({'x.weight': {'dtype': 'F32', 'shape': [2, 2],
                                         'data_offsets': [0, 16]}}).encode()
            p.write_bytes(struct.pack('<Q', len(h)) + h + struct.pack('<4f', 1., 2., 3., 4.))
            info = audit.source_offsets(p)
            self.assertEqual(info['x.weight']['offset'], 8 + len(h))

    def test_non_f32_source_red(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'model.safetensors'
            h = json.dumps({'x.weight': {'dtype': 'BF16', 'shape': [2],
                                         'data_offsets': [0, 4]}}).encode()
            p.write_bytes(struct.pack('<Q', len(h)) + h + b'0' * 4)
            with self.assertRaisesRegex(ValueError, 'non-F32'):
                audit.source_offsets(p)

    def test_truncated_tensor_data_red(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'model.safetensors'
            h = json.dumps({'x.weight': {'dtype': 'F32', 'shape': [4],
                                         'data_offsets': [0, 16]}}).encode()
            p.write_bytes(struct.pack('<Q', len(h)) + h + b'0' * 4)
            with self.assertRaisesRegex(ValueError, 'data range'):
                audit.source_offsets(p)

    def test_wrong_pinned_master_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            master = Path(d) / 'master'
            master.mkdir()
            (master / 'model.safetensors').write_bytes(b'not qad master')
            gg = Path(d) / 'gguf'
            gg.write_bytes(b'not gguf')
            out = Path(d) / 'result.json'
            self.assertEqual(audit.main(['--master', str(master), '--gguf', str(gg),
                                         '--output', str(out)]), 2)
            self.assertEqual(json.loads(out.read_text())['status'], 'VALUE_AUDIT_RED')

    def test_receipt_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            master = Path(d) / 'master'
            master.mkdir()
            (master / 'model.safetensors').write_bytes(b'bad')
            gg = Path(d) / 'gguf'
            gg.write_bytes(b'bad')
            out = Path(d) / 'result.json'
            out.write_text('old failed attempt')
            with self.assertRaises(FileExistsError):
                audit.main(['--master', str(master), '--gguf', str(gg),
                            '--output', str(out)])
            self.assertEqual(out.read_text(), 'old failed attempt')


if __name__ == '__main__':
    unittest.main()
