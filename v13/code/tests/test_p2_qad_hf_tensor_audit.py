"""Isolated source-only P2 structural audit tests (no GGUF/model downloads)."""
import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'p2_qad_hf_tensor_audit.py'
spec = importlib.util.spec_from_file_location('p2_audit', SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def sample():
    hf = {'layer.weight': {'shape': [2, 3], 'dtype': 'F32'}}
    gg = {'block.weight': {'shape': [3, 2], 'type': 'Q4_0'}}
    return hf, gg, lambda x: {'layer': 'block'}.get(x)


class AuditTests(unittest.TestCase):
    def test_matching_shape_only_never_claims_parity(self):
        result = audit.compare(*sample())
        self.assertEqual(result['status'], 'STRUCTURE_MATCH_PARITY_UNPROVEN')
        self.assertIn('native logits', result['unproven'])

    def test_reversed_dimensions_rejected(self):
        hf, gg, m = sample()
        gg['block.weight']['shape'] = [2, 3]
        self.assertEqual(len(audit.compare(hf, gg, m)['shape_mismatch']), 1)

    def test_missing_required_weight_rejected(self):
        hf, gg, m = sample()
        self.assertEqual(audit.compare(hf, {}, m)['status'], 'STRUCTURE_RED')

    def test_unmapped_weight_rejected(self):
        hf, gg, m = sample()
        self.assertEqual(audit.compare(hf, gg, lambda _: None)['unmapped_hf'], ['layer.weight'])

    def test_duplicate_mapping_rejected(self):
        hf, gg, m = sample()
        hf['other.weight'] = {'shape': [2, 3], 'dtype': 'F32'}
        result = audit.compare(hf, gg, lambda _: 'block')
        self.assertEqual(len(result['collisions']), 1)

    def test_gguf_extra_requires_review(self):
        hf, gg, m = sample()
        gg['unrelated.weight'] = {'shape': [1], 'type': 'F32'}
        self.assertEqual(audit.compare(hf, gg, m)['unaccounted_gguf'], ['unrelated.weight'])

    def test_nonweight_requires_review(self):
        hf, gg, m = sample()
        hf['layer.bias'] = {'shape': [2], 'dtype': 'F32'}
        self.assertEqual(audit.compare(hf, gg, m)['unmapped_hf'], ['layer.bias'])

    def test_header_reads_metadata_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'model.safetensors'
            hdr = json.dumps({'layer.weight': {'dtype': 'F32', 'shape': [2, 3],
                                              'data_offsets': [0, 24]}}).encode()
            p.write_bytes(struct.pack('<Q', len(hdr)) + hdr + b'0' * 24)
            self.assertEqual(audit.safetensors_header(p)['layer.weight']['shape'], [2, 3])

    def test_truncated_header_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'model.safetensors'
            p.write_bytes(struct.pack('<Q', 12) + b'{}')
            with self.assertRaises(ValueError):
                audit.safetensors_header(p)

    def test_main_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            master = Path(d) / 'master'
            master.mkdir()
            (master / 'model.safetensors').write_bytes(b'not master')
            gg = Path(d) / 'model.gguf'
            gg.write_bytes(b'not gguf')
            out = Path(d) / 'report.json'
            self.assertEqual(audit.main(['--master', str(master), '--gguf', str(gg),
                                         '--output', str(out)]), 2)
            self.assertEqual(json.loads(out.read_text())['status'], 'STRUCTURE_RED')


    def test_receipt_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            master = Path(d) / 'master'
            master.mkdir()
            (master / 'model.safetensors').write_bytes(b'not master')
            gg = Path(d) / 'model.gguf'
            gg.write_bytes(b'not gguf')
            out = Path(d) / 'report.json'
            out.write_text('original failed attempt')
            with self.assertRaises(FileExistsError):
                audit.main(['--master', str(master), '--gguf', str(gg),
                            '--output', str(out)])
            self.assertEqual(out.read_text(), 'original failed attempt')

    def test_symlinked_model_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            master = Path(d) / 'master'
            master.mkdir()
            (master / 'model.safetensors').write_bytes(b'not master')
            gg = Path(d) / 'model.gguf'
            gg.symlink_to(master / 'model.safetensors')
            with self.assertRaisesRegex(ValueError, 'symlinked'):
                audit.audit(master, gg)

if __name__ == '__main__':
    unittest.main()
