"""Sparse trainer readiness agrees with runtime after native library drift; authored files only."""
import json
from pathlib import Path
import tempfile
import unittest

from v13.agi.trainers import _memory_server_ok
from v13.common import file_hash
from v13.memory_server import MANIFEST, runtime_library_hashes, runner_memory


class SparseTrainerNativeBinding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.home = Path(self.tmp.name)
        (self.home/'bin').mkdir(); (self.home/'config').mkdir()
        self.binary = self.home/'bin/llama-server-mem'; self.binary.write_bytes(b'authored launcher')
        self.model = self.home/'model.gguf'; self.model.write_bytes(b'authored model')
        self.memory = self.home/'memory.bin'; self.memory.write_bytes(b'authored memory')
        (self.home/'config/lora-active.json').write_text(json.dumps({'C3_LANGUAGE#sparse_memory':{
            'path':str(self.memory), 'sha256':file_hash(self.memory),
            'base_model_sha256':file_hash(self.model)}}))

    def tearDown(self):
        self.tmp.cleanup()

    def bind(self, legacy=False):
        manifest = {'binary_sha256':file_hash(self.binary)}
        if not legacy:
            manifest['runtime_libraries_sha256'] = runtime_library_hashes(self.binary)
        (self.home/MANIFEST).write_text(json.dumps(manifest))

    def assert_agreement(self, expected):
        self.assertIs(_memory_server_ok(self.home), expected)
        self.assertIs(runner_memory(self.home, 'C3_LANGUAGE', self.model) is not None, expected)

    def test_matching_build_and_changed_hook_with_identical_launcher(self):
        library = self.home/'bin/libhook.so'; library.write_bytes(b'hook v1')
        launcher = file_hash(self.binary); self.bind(); self.assert_agreement(True)
        library.write_bytes(b'hook v2')
        self.assertEqual(file_hash(self.binary), launcher); self.assert_agreement(False)
        self.bind(); self.assert_agreement(True)  # rebuilt manifest restores capability

    def test_added_and_removed_libraries_are_binding_changes(self):
        self.bind(); self.assert_agreement(True)
        library = self.home/'bin/libhook.so'; library.write_bytes(b'new hook')
        self.assert_agreement(False); self.bind(); self.assert_agreement(True)
        library.unlink(); self.assert_agreement(False)

    def test_versioned_library_and_symlink_alias_are_both_bound(self):
        real = self.home/'bin/libhook.so.1'; real.write_bytes(b'hook v1')
        (self.home/'bin/libhook.so').symlink_to(real.name)
        self.bind(); self.assert_agreement(True)
        real.write_bytes(b'hook v2'); self.assert_agreement(False)

    def test_legacy_manifest_without_libraries_only_accepts_static_build(self):
        self.bind(legacy=True); self.assert_agreement(True)
        (self.home/'bin/libhook.so').write_bytes(b'dynamic hook')
        self.assert_agreement(False)

    def test_changed_launcher_and_missing_manifest_remain_unavailable(self):
        self.bind(); self.binary.write_bytes(b'changed launcher'); self.assert_agreement(False)
        (self.home/MANIFEST).unlink(); self.assert_agreement(False)


if __name__ == '__main__':
    unittest.main()
