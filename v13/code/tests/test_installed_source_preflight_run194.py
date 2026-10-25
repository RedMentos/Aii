"""Run194 extracted Phone ZIP installer preflight: software integrity only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts import verify_installed_source_run194 as V

ROOT = Path(__file__).resolve().parents[1]


class Preflight(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'V13-Phone'
        self.root.mkdir()
        self.files = {name: ('safe source: ' + name + '\n').encode() for name in V.REQUIRED}
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        for name, body in self.files.items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
        manifest = {'schema_version': 1,
                    'files': {p: hashlib.sha256(b).hexdigest() for p, b in self.files.items()}}
        (self.root / 'WORKSPACE_FILES.json').write_text(json.dumps(manifest))

    def test_valid_source_tree_is_accepted_without_authority(self):
        result = V.verify(self.root)
        self.assertEqual(result['status'], 'EXTRACTED_SOURCE_INTEGRITY_PASS')
        self.assertFalse(result['authenticity_proven'])
        self.assertFalse(result['canonical_gate_pass'])
        self.assertEqual(result['files'], len(self.files))

    def test_mutated_registered_file_fails_closed(self):
        (self.root / 'setup.sh').write_text('malicious change')
        with self.assertRaisesRegex(ValueError, 'SOURCE_HASH_MISMATCH'):
            V.verify(self.root)

    def test_unregistered_executable_source_is_rejected(self):
        (self.root / 'new_script.py').write_text('print(1)')
        with self.assertRaisesRegex(ValueError, 'UNREGISTERED_SOURCE_FILE'):
            V.verify(self.root)

    def test_unregistered_python_cache_is_ignored_but_symlink_is_not(self):
        cache = self.root / 'v13/__pycache__'
        cache.mkdir(parents=True)
        (cache / 'module.cpython-313.pyc').write_bytes(b'cache')
        V.verify(self.root)
        (cache / 'bad.pyc').symlink_to(self.root / 'setup.sh')
        with self.assertRaisesRegex(ValueError, 'SOURCE_SYMLINK_FORBIDDEN'):
            V.verify(self.root)

    def test_missing_or_duplicate_manifest_is_rejected(self):
        manifest = self.root / 'WORKSPACE_FILES.json'
        manifest.unlink()
        with self.assertRaisesRegex(ValueError, 'SOURCE_MANIFEST_MISSING'):
            V.verify(self.root)
        manifest.write_text('{"schema_version":1,"schema_version":1,"files":{}}')
        with self.assertRaisesRegex(ValueError, 'SOURCE_MANIFEST_INVALID'):
            V.verify(self.root)

    def test_traversal_and_private_payload_cannot_enter_manifest(self):
        for name in ('../escape.py', 'private.gguf', 'scripts\\bad.py', '/tmp/x'):
            with self.subTest(name=name):
                files = {**self.files, name: b'bad'}
                manifest = {'schema_version': 1,
                            'files': {p: hashlib.sha256(b).hexdigest() for p, b in files.items()}}
                (self.root / 'WORKSPACE_FILES.json').write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):
                    V.verify(self.root)

    def test_installer_checks_before_pip_and_v13_bootstrap(self):
        text = (ROOT / 'setup.sh').read_text()
        marker = 'scripts/verify_installed_source_run194.py'
        self.assertIn(marker, text)
        self.assertIn(' -I -S ', text)
        self.assertLess(text.index(marker), text.index(' -m pip install '))
        self.assertLess(text.index(marker), text.index(' -m v13.bootstrap '))

    def test_real_extracted_phone_archive_is_verified_when_present(self):
        # In the source checkout no generated manifest exists; in the Phone
        # ZIP it does and this test validates the actual complete source tree.
        if not (ROOT / 'WORKSPACE_FILES.json').exists():
            self.skipTest('Source checkout is not a packaged Phone ZIP')
        result = V.verify(ROOT)
        self.assertGreaterEqual(result['files'], 100)


if __name__ == '__main__':
    unittest.main()
