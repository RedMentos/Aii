"""LP3 real-master smoke source guards only; no model downloads."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from scripts.lp3_real_master_smoke import MASTER_SHA256, verify_master, main, PROMPTS, TARGETS


class RealMasterSmokeSourceTests(unittest.TestCase):
    def test_public_master_pin_and_synthetic_examples(self):
        self.assertEqual(len(MASTER_SHA256), 64)
        self.assertEqual(len(PROMPTS), len(TARGETS))
        self.assertEqual(len(PROMPTS), 2)
        self.assertNotEqual(PROMPTS[0], PROMPTS[1])

    def test_master_preflight_rejects_bad_hash_and_missing_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(ValueError):
                verify_master(root)
            (root / 'model.safetensors').write_bytes(b'fake')
            with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
                verify_master(root)
            with self.assertRaisesRegex(ValueError, 'metadata'):
                verify_master(root, expected=hashlib.sha256(b'fake').hexdigest())
            for name in ('config.json', 'tokenizer.json', 'tokenizer_config.json'):
                (root / name).write_text('{}')
            self.assertEqual(verify_master(root, expected=hashlib.sha256(b'fake').hexdigest()),
                             hashlib.sha256(b'fake').hexdigest())

    def test_execution_requires_explicit_flag(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'Explicit'):
                main(['--master', d, '--out', str(Path(d)/'result.json')])


if __name__ == '__main__':
    unittest.main()
