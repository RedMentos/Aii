import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from v13.common import APP, file_hash

spec = importlib.util.spec_from_file_location('audit_native_ports', APP / 'scripts/audit_native_ports.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def text(value):
    raw = value.encode()
    return struct.pack('<Q', len(raw)) + raw


class NativePortAuditTests(unittest.TestCase):
    def test_gguf_reads_real_header_and_tensor_parameters_without_weights(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'model.gguf'
            data = b'GGUF' + struct.pack('<IQQ', 3, 2, 3)
            data += text('general.architecture') + struct.pack('<I', 8) + text('lfm2')
            data += text('lfm2.embedding_length') + struct.pack('<II', 4, 1024)
            data += text('tokenizer.ggml.tokens') + struct.pack('<IIQ', 9, 8, 2) + text('hello') + text('bye')
            data += text('output_norm.weight') + struct.pack('<IQIQ', 1, 1024, 0, 0)
            data += text('output.weight') + struct.pack('<IQQIQ', 2, 1024, 65536, 2, 4096)
            path.write_bytes(data)
            observed = audit.inspect_gguf(path)
            self.assertEqual(observed['stored_parameter_elements'], 1024 + 1024 * 65536)
            self.assertEqual(observed['tensor_types'], {0:1, 2:1})
            self.assertEqual(observed['metadata']['tokenizer.ggml.tokens'], {'item_type':8, 'length':2})
            self.assertFalse(observed['train_master_proven'])
            self.assertFalse(observed['weight_payload_loaded'])

    def test_malformed_header_refuses_unbounded_allocation_or_truncation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'model.gguf'
            for raw in (b'GGUF', b'GGUF' + struct.pack('<IQQQ', 3, 0, 1, 2**40)):
                path.write_bytes(raw)
                with self.assertRaises(ValueError): audit.inspect_gguf(path)

    def test_library_optimizer_symbol_never_grants_training_proof(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'libllama.so'; path.write_bytes(b'symbol fixture')
            completed = SimpleNamespace(returncode=0, stderr='', stdout='0001 T llama_opt_init\n0002 T llama_opt_epoch\n')
            with patch.object(audit.shutil, 'which', return_value='/usr/bin/nm'), patch.object(audit.subprocess, 'run', return_value=completed):
                observed = audit.inspect_symbols(path)
            self.assertTrue(observed['symbols']['llama_opt_init'])
            self.assertFalse(observed['train_runner_proven'])
            self.assertEqual(observed['sha256'], file_hash(path))
            self.assertFalse(audit.absent_ports()['native_body_training']['available'])

    def test_no_model_is_unavailable_and_never_native_probed(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            with patch.object(audit, 'probe_role', side_effect=AssertionError('Must not probe missing models')):
                report = audit.audit(home, probe_native=True)
            self.assertIsNone(report['train_runner_proof'])
            self.assertEqual(report['native_body_update_authority'], 0)
            self.assertTrue(all(row['status'] == 'UNAVAILABLE' for row in report['roles'].values()))

    def test_modified_installed_artifact_is_measured_and_blocks_native_probe(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder); (home / 'config').mkdir(); (home / 'models').mkdir()
            path = home / 'models/needle.cact'; path.write_bytes(b'changed')
            (home / 'config/models.json').write_text(json.dumps({'needle':{
                'model_id':'fixture', 'exact_revision':'fixture', 'main_file':'needle.cact',
                'files':{'needle.cact':{'path':'models/needle.cact','size':7,'sha256':'0' * 64}}}}))
            with patch.object(audit, 'probe_role', side_effect=AssertionError('Must not probe tampered models')):
                report = audit.audit(home, probe_native=True)
            entry = report['roles']['C2_CONTROL']
            self.assertEqual(entry['status'], 'ARTIFACTS_UNVERIFIED')
            self.assertEqual(entry['artifacts']['needle.cact']['sha256'], file_hash(path))
            self.assertIsNone(entry['ports'])
