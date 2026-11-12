"""Isolated staging tests; actual V13 end-to-end suite is separate."""
import importlib.util
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts/stage_integrated_candidate.py'
spec = importlib.util.spec_from_file_location('stage_candidate', MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StageTest(unittest.TestCase):
    def setUp(self):
        original_pin = module.BUILDER_SHA
        self.addCleanup(setattr, module, 'BUILDER_SHA', original_pin)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.code = self.root / 'code'
        (self.code / 'scripts').mkdir(parents=True)
        (self.code / 'v13').mkdir()
        (self.code / 'v13/runtime.py').write_text('ORIGINAL')
        (self.code / 'specs').mkdir()
        (self.code / 'specs/test.json').write_text('{}')

    def builder(self, body):
        source = 'def build_sources(code_dir):\n' + body
        (self.code / module.BUILDER).write_text(source)
        module.BUILDER_SHA = hashlib.sha256(source.encode()).hexdigest()

    def test_stages_replacement_without_mutating_source(self):
        self.builder("    return {'v13/runtime.py': b'INTEGRATED'}\n")
        out = self.root / 'candidate'
        result = module.stage(self.code, out)
        self.assertEqual((out / 'v13/runtime.py').read_text(), 'INTEGRATED')
        self.assertEqual((self.code / 'v13/runtime.py').read_text(), 'ORIGINAL')
        self.assertEqual(result['status'], 'SHADOW_REVIEW_ONLY')
        self.assertTrue((out / 'specs/test.json').exists())
        with self.assertRaises(FileExistsError):
            module.stage(self.code, out)

    def test_pin_failure_never_publishes_candidate(self):
        self.builder("    raise ValueError('pin mismatch')\n")
        out = self.root / 'candidate'
        with self.assertRaisesRegex(ValueError, 'pin mismatch'):
            module.stage(self.code, out)
        self.assertFalse(out.exists())

    def test_rejects_traversal_before_copy(self):
        self.builder("    return {'../outside.py': b'bad'}\n")
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            module.stage(self.code, self.root / 'candidate')
        self.assertFalse((self.root / 'outside.py').exists())

    def test_changed_builder_is_rejected_before_import(self):
        self.builder("    return {}\n")
        marker = self.root / 'executed'
        source = 'from pathlib import Path\nPath(' + repr(str(marker)) + ').touch()\n'
        with (self.code / module.BUILDER).open('a') as stream:
            stream.write(source)
        with self.assertRaisesRegex(ValueError, 'builder hash mismatch'):
            module.stage(self.code, self.root / 'candidate')
        self.assertFalse(marker.exists())

    def test_rejects_every_source_descendant(self):
        self.builder("    return {}\n")
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            module.stage(self.code, self.code / 'v13/nested/candidate')
        self.assertFalse((self.code / 'v13/nested').exists())

    def test_skips_runtime_database_and_model_artifacts(self):
        self.builder("    return {}\n")
        for name in ('brain.sqlite3', 'adapter.pt', 'model.safetensors', 'model.gguf'):
            (self.code / 'v13' / name).write_bytes(b'synthetic-private-artifact')
        dest = self.root / 'candidate'
        result = module.stage(self.code, dest)
        self.assertEqual(set(result['files_sha256']), {
            'v13/runtime.py', 'specs/test.json', module.BUILDER})
        self.assertFalse((dest / 'v13/brain.sqlite3').exists())

    def test_symlink_is_not_followed_or_published(self):
        self.builder("    return {}\n")
        external = self.root / 'external'
        external.write_text('retain')
        (self.code / 'v13/external.py').symlink_to(external)
        with self.assertRaisesRegex(ValueError, 'contains a symlink'):
            module.stage(self.code, self.root / 'candidate')
        self.assertEqual(external.read_text(), 'retain')
        self.assertFalse((self.root / 'candidate').exists())

    def test_concurrent_empty_destination_is_preserved(self):
        self.builder("    return {}\n")
        dest = self.root / 'candidate'
        publish = module._publish
        inodes = []
        def competing_destination(staging, destination):
            destination.mkdir()
            inodes.append(destination.stat().st_ino)
            return publish(staging, destination)
        with patch.object(module, '_publish', side_effect=competing_destination):
            with self.assertRaises(FileExistsError):
                module.stage(self.code, dest)
        self.assertEqual(dest.stat().st_ino, inodes[0])
        self.assertEqual(list(dest.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
