"""Isolated staging tests; actual V13 end-to-end suite is separate."""
import importlib.util
import hashlib
import re
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
        original_overlay_pin = module.ARITHMETIC_OVERLAY_GIT_BLOB
        self.addCleanup(setattr, module, 'ARITHMETIC_OVERLAY_GIT_BLOB', original_overlay_pin)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.code = self.root / 'code'
        (self.code / 'scripts').mkdir(parents=True)
        (self.code / 'v13').mkdir()
        (self.code / 'v13/runtime.py').write_text('ORIGINAL')
        (self.code / 'v13/fast_greeting.py').write_bytes(b'FAST_GREETING')
        overlay = (
            "SOURCE_PINS = {}\n"
            "def apply_staged_arithmetic(code_dir, staged_root):\n"
            "    return {'v13/runtime.py': (staged_root / 'v13/runtime.py').read_bytes() + b'\\nARITHMETIC'}\n"
        ).encode('utf-8')
        overlay_path = self.code / module.ARITHMETIC_OVERLAY
        overlay_path.write_bytes(overlay)
        module.ARITHMETIC_OVERLAY_GIT_BLOB = hashlib.sha1(
            b'blob ' + str(len(overlay)).encode('ascii') + b'\0' + overlay
        ).hexdigest()
        (self.code / 'specs').mkdir()
        (self.code / 'specs/test.json').write_text('{}')

    def builder(self, body):
        body = body.replace('return ', 'result = ', 1) if 'return ' in body else body
        source = (
            'def build_sources(code_dir):\n' + body
            + "    result.setdefault('v13/runtime.py', b'ORIGINAL')\n"
            + "    result['v13/runtime.py'] += b'\\nEXACT_GREETING_ACK'\n"
            + "    result.setdefault('v13/fast_greeting.py', b'FAST_GREETING')\n"
            + '    return result\n'
        )
        (self.code / module.BUILDER).write_text(source)
        module.BUILDER_SHA = hashlib.sha256(source.encode()).hexdigest()

    def test_stages_replacement_without_mutating_source(self):
        self.builder("    return {'v13/runtime.py': b'INTEGRATED'}\n")
        out = self.root / 'candidate'
        result = module.stage(self.code, out)
        staged_runtime = (out / 'v13/runtime.py').read_bytes()
        self.assertTrue(staged_runtime.startswith(b'INTEGRATED'))
        self.assertIn(b'EXACT_GREETING_ACK', staged_runtime)
        self.assertIn(b'ARITHMETIC', staged_runtime)
        self.assertEqual((self.code / 'v13/runtime.py').read_text(), 'ORIGINAL')
        self.assertEqual(result['status'], 'SHADOW_REVIEW_ONLY')
        self.assertTrue((out / 'specs/test.json').exists())
        with self.assertRaises(FileExistsError):
            module.stage(self.code, out)

    def test_nested_builder_hash_pins_match_real_bytes(self):
        code = Path(__file__).resolve().parents[1]
        recovery = code / module.BUILDER
        stage_bytes = MODULE_PATH.read_bytes()
        self.assertEqual(module.BUILDER_SHA, hashlib.sha256(recovery.read_bytes()).hexdigest())
        deploy_source = (code / 'v13/runtime_deploy.py').read_text()
        match = re.search(r"""STAGER_SHA256 = ["']([a-f0-9]{64})["']""", deploy_source)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), hashlib.sha256(stage_bytes).hexdigest())

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
            'v13/runtime.py', 'v13/fast_greeting.py', 'specs/test.json', module.BUILDER, module.ARITHMETIC_OVERLAY})
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
