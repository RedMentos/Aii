"""Isolated staging tests; actual V13 end-to-end suite is separate."""
import importlib.util
import hashlib
import re
import shutil
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
        original_probe_pin = module.NATIVE_PROBE_OVERLAY_GIT_BLOB
        self.addCleanup(setattr, module, 'NATIVE_PROBE_OVERLAY_GIT_BLOB', original_probe_pin)
        original_close_pin = module.RUNTIME_CLOSE_OVERLAY_GIT_BLOB
        self.addCleanup(setattr, module, 'RUNTIME_CLOSE_OVERLAY_GIT_BLOB', original_close_pin)
        original_action_pin = module.ACTION_SELECTION_LINEAGE_OVERLAY_GIT_BLOB
        self.addCleanup(setattr, module, 'ACTION_SELECTION_LINEAGE_OVERLAY_GIT_BLOB', original_action_pin)
        original_tokenwise_pin = module.TOKENWISE_PAIR_OVERLAY_GIT_BLOB
        self.addCleanup(setattr, module, 'TOKENWISE_PAIR_OVERLAY_GIT_BLOB', original_tokenwise_pin)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.code = self.root / 'code'
        (self.code / 'scripts').mkdir(parents=True)
        (self.code / 'v13').mkdir()
        (self.code / 'v13/runtime.py').write_text('ORIGINAL')
        source_code = Path(__file__).resolve().parents[1]
        shutil.copy2(source_code / 'v13/focal.py', self.code / 'v13/focal.py')
        shutil.copy2(source_code / 'v13/operator.py', self.code / 'v13/operator.py')
        shutil.copy2(source_code / 'v13/native_probe_approval.py', self.code / 'v13/native_probe_approval.py')
        shutil.copy2(source_code / 'v13/native_probe_matrix.py', self.code / 'v13/native_probe_matrix.py')
        for name in ('runners.py', 'cognition.py', 'callosum.py'):
            shutil.copy2(source_code / ('v13/' + name), self.code / 'v13/' / name)
        shutil.copy2(source_code / module.NATIVE_PROBE_OVERLAY, self.code / module.NATIVE_PROBE_OVERLAY)
        shutil.copy2(source_code / module.RUNTIME_CLOSE_OVERLAY, self.code / module.RUNTIME_CLOSE_OVERLAY)
        shutil.copy2(source_code / module.ACTION_SELECTION_LINEAGE_OVERLAY, self.code / module.ACTION_SELECTION_LINEAGE_OVERLAY)
        tokenwise = (
            "def apply_staged_tokenwise(code_dir, staging):\n"
            "    return {\n"
            "        'v13/runners.py': (staging / 'v13/runners.py').read_bytes() + b'TOKENWISE_TOKENIZER',\n"
            "        'v13/cognition.py': (staging / 'v13/cognition.py').read_bytes() + b'TOKENWISE_CONSUMER',\n"
            "        'v13/callosum.py': (staging / 'v13/callosum.py').read_bytes() + b'TOKENWISE_COMMAND',\n"
            "        'v13/native_probe_approval.py': (staging / 'v13/native_probe_approval.py').read_bytes() + b'TOKENWISE_PURPOSE',\n"
            "    }\n"
        ).encode('utf-8')
        tokenwise_path = self.code / module.TOKENWISE_PAIR_OVERLAY
        tokenwise_path.write_bytes(tokenwise)
        module.TOKENWISE_PAIR_OVERLAY_GIT_BLOB = hashlib.sha1(
            b'blob ' + str(len(tokenwise)).encode('ascii') + b'\0' + tokenwise
        ).hexdigest()
        overlay = (
            "SOURCE_PINS = {}\n"
            "def apply_staged_arithmetic(code_dir, staged_root):\n"
            "    return {'v13/runtime.py': b'INTEGRATED guard_runtime_close(self)'}\n"
        ).encode('utf-8')
        overlay_path = self.code / module.ARITHMETIC_OVERLAY
        overlay_path.write_bytes(overlay)
        module.ARITHMETIC_OVERLAY_GIT_BLOB = hashlib.sha1(
            b'blob ' + str(len(overlay)).encode('ascii') + b'\0' + overlay
        ).hexdigest()
        (self.code / 'specs').mkdir()
        (self.code / 'specs/test.json').write_text('{}')

    def builder(self, body):
        indented = ''.join('    ' + line for line in body.splitlines(True))
        source = ('def build_sources(code_dir):\n'
                  '    result = {"v13/runtime.py": b"guard_runtime_close(self)"}\n'
                  '    result["v13/focal.py"] = (code_dir / "v13/focal.py").read_bytes() + b"\n# SCALE_AWARE_C4_RULE\n"\n'
                  '    def custom(code_dir):\n' + indented +
                  '    extra = custom(code_dir)\n'
                  '    if isinstance(extra, dict): result.update(extra)\n'
                  '    return result\n')
        (self.code / module.BUILDER).write_text(source)
        module.BUILDER_SHA = hashlib.sha256(source.encode()).hexdigest()

    def test_stages_replacement_without_mutating_source(self):
        self.builder("    return {'v13/runtime.py': b'INTEGRATED guard_runtime_close(self)'}\n")
        out = self.root / 'candidate'
        source_focal = (self.code / 'v13/focal.py').read_bytes()
        result = module.stage(self.code, out)
        self.assertEqual((out / 'v13/runtime.py').read_text(), 'INTEGRATED guard_runtime_close(self)')
        self.assertEqual((self.code / 'v13/runtime.py').read_text(), 'ORIGINAL')
        self.assertEqual(result['status'], 'SHADOW_REVIEW_ONLY')
        source_operator = (self.code / 'v13/operator.py').read_bytes()
        staged_operator = (out / 'v13/operator.py').read_bytes()
        self.assertNotEqual(staged_operator, source_operator)
        self.assertIn(b'arm-probe <sender> <receiver>', staged_operator)
        self.assertEqual(result['native_probe_overlay']['status'], 'SHADOW_REVIEW_ONLY')
        self.assertEqual(result['native_probe_overlay']['replaced_files'], ['v13/operator.py'])
        self.assertEqual(result['native_probe_close_overlay']['status'], 'SHADOW_REVIEW_ONLY')
        self.assertEqual(result['native_probe_close_overlay']['replaced_files'], ['v13/runtime.py'])
        self.assertEqual(result['action_selection_lineage_overlay']['status'], 'SHADOW_REVIEW_ONLY')
        self.assertEqual(result['action_selection_lineage_overlay']['replaced_files'], ['v13/focal.py'])
        self.assertEqual(result['native_tokenwise_pair_overlay']['status'], 'SHADOW_REVIEW_ONLY')
        self.assertEqual(result['native_tokenwise_pair_overlay']['replaced_files'], [
            'v13/callosum.py', 'v13/cognition.py', 'v13/native_probe_approval.py', 'v13/runners.py'])
        self.assertIn(b'TOKENWISE_TOKENIZER', (out / 'v13/runners.py').read_bytes())
        self.assertIn(b'TOKENWISE_CONSUMER', (out / 'v13/cognition.py').read_bytes())
        self.assertIn(b'TOKENWISE_COMMAND', (out / 'v13/callosum.py').read_bytes())
        self.assertEqual((self.code / 'v13/focal.py').read_bytes(), source_focal)
        self.assertIn(b'ACTION_SELECTION_C1_BROADCAST_LINEAGE_V1', (out / 'v13/focal.py').read_bytes())
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

    def test_real_repo_stage_applies_tokenwise_runtime_overlay(self):
        code = Path(__file__).resolve().parents[1]
        destination = self.root / 'real-candidate'
        result = module.stage(code, destination)
        self.assertEqual(result['status'], 'SHADOW_REVIEW_ONLY')
        self.assertIn('native_tokenwise_pair_overlay', result)
        self.assertEqual(result['native_tokenwise_pair_overlay']['training_authority'], 0)
        self.assertEqual(result['native_tokenwise_pair_overlay']['native_receiver_authority'], 0)
        self.assertIn(b'def tokenize_with_pieces(', (destination / 'v13/runners.py').read_bytes())
        self.assertIn(b'def native_tokenwise_pair_probe(', (destination / 'v13/cognition.py').read_bytes())
        self.assertIn(b'arm-tokenwise', (destination / 'v13/callosum.py').read_bytes())
        self.assertIn(b'TOKENWISE_PAIR_DIAGNOSTIC', (destination / 'v13/native_probe_approval.py').read_bytes())
        self.assertFalse((destination / 'v13/native_input_embedding_extractor').exists())

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
            'v13/runtime.py', 'v13/operator.py', 'v13/native_probe_approval.py',
            'v13/native_probe_matrix.py', 'v13/focal.py', 'specs/test.json', module.BUILDER,
            module.ARITHMETIC_OVERLAY, module.NATIVE_PROBE_OVERLAY, module.RUNTIME_CLOSE_OVERLAY,
            module.ACTION_SELECTION_LINEAGE_OVERLAY, module.TOKENWISE_PAIR_OVERLAY,
            'v13/runners.py', 'v13/cognition.py', 'v13/callosum.py'})
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
