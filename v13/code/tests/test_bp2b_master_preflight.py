"""BP2b local SHA-bound model preflight: synthetic files, no model load."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import bp2b_master_preflight as mp


class MasterPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.master = self.root / 'master'
        self.master.mkdir()
        self.metadata = {}
        for name in mp.METADATA:
            data = ('metadata-' + name).encode()
            (self.master/name).write_bytes(data)
            self.metadata[name] = {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        self.model = b'model-bytes-synthetic'
        (self.master/'model.safetensors').write_bytes(self.model)
        self.pin = {'schema': mp.PIN_SCHEMA, 'model_id': 'LiquidAI/LFM2.5-1.2B-Instruct',
                    'revision': '8c1348a4aac046a3a5d7698e7fcaaa8a3b7d9cdf',
                    'license_id': 'LFM Open License 1.0',
                    'model_safetensors_sha256': hashlib.sha256(self.model).hexdigest(),
                    'model_weights_sha256_verified_locally': False,
                    'metadata': self.metadata, 'evidence': {'synthetic': True}}
        self.pinpath = self.root / 'pin.json'
        self.save_pin()

    def save_pin(self):
        self.pinpath.write_text(json.dumps(self.pin, sort_keys=True))

    def test_full_file_hash_pass_without_model_load(self):
        result = mp.verify(self.master, self.pinpath)
        self.assertEqual(result['status'], 'FULL_FILE_HASH_PASS')
        self.assertTrue(result['master_sha256_verified_locally'])
        self.assertFalse(result['model_loaded'])
        self.assertFalse(result['training_performed'])
        self.assertEqual(result['learning_authority'], 0)
        self.assertEqual(set(result['metadata']), set(mp.METADATA))

    def test_metadata_only_does_not_need_weights(self):
        (self.master/'model.safetensors').unlink()
        result = mp.verify(self.master, self.pinpath, metadata_only=True)
        self.assertEqual(result['status'], 'METADATA_ONLY_PASS')
        self.assertFalse(result['master_sha256_verified_locally'])

    def test_corrupted_metadata_and_wrong_weights_fail(self):
        (self.master/'tokenizer.json').write_bytes(b'tampered')
        with self.assertRaises(ValueError):
            mp.verify(self.master, self.pinpath, metadata_only=True)
        (self.master/'tokenizer.json').write_bytes(b'metadata-tokenizer.json')
        (self.master/'model.safetensors').write_bytes(b'wrong')
        with self.assertRaises(ValueError):
            mp.verify(self.master, self.pinpath)

    def test_missing_symlinked_or_oversized_metadata_fail(self):
        p = self.master/'config.json'
        p.unlink()
        with self.assertRaises(ValueError):
            mp.verify(self.master, self.pinpath, metadata_only=True)
        target = self.root/'config-real'
        target.write_bytes(b'metadata-config.json')
        p.symlink_to(target)
        with self.assertRaises(ValueError):
            mp.verify(self.master, self.pinpath, metadata_only=True)
        p.unlink()
        p.write_bytes(b'metadata-config.json')
        self.pin['metadata']['config.json']['size'] = mp.MAX_METADATA_BYTES + 1
        self.save_pin()
        with self.assertRaises(ValueError):
            mp.verify(self.master, self.pinpath, metadata_only=True)

    def test_invalid_pin_schema_duplicate_nonfinite_or_extra_file_fail(self):
        self.pinpath.write_text('{"schema":"x","schema":"y"}')
        with self.assertRaises(ValueError):
            mp.load_pin(self.pinpath)
        self.pinpath.write_text('{"schema":NaN}')
        with self.assertRaises(ValueError):
            mp.load_pin(self.pinpath)
        self.pin['metadata']['unexpected'] = {'sha256': '0'*64, 'size': 1}
        self.save_pin()
        with self.assertRaises(ValueError):
            mp.load_pin(self.pinpath)

    def test_immutable_receipt_replay(self):
        out = self.root/'report.json'
        argv = ['--master-dir', str(self.master), '--pin', str(self.pinpath),
                '--metadata-only', '--out', str(out)]
        self.assertEqual(mp.main(argv), 0)
        self.assertEqual(mp.main(argv), 0)
        self.assertEqual(json.loads(out.read_text())['status'], 'METADATA_ONLY_PASS')
        out.write_text('tampered')
        with self.assertRaises(ValueError):
            mp.main(argv)

    def test_real_locked_pin_is_well_formed_but_not_weight_verified(self):
        path = Path(__file__).resolve().parents[1] / 'specs' / 'bp2b_master_metadata.json'
        pin, sha = mp.load_pin(path)
        self.assertEqual(len(pin['metadata']), 7)
        self.assertEqual(len(sha), 64)
        self.assertEqual(pin['model_safetensors_sha256'],
                         '1ba63d9adb03ae43581db0e136e4416febe0441aff7296397bd455fb6017f73a')
        self.assertFalse(pin['model_weights_sha256_verified_locally'])


if __name__ == '__main__':
    unittest.main()
