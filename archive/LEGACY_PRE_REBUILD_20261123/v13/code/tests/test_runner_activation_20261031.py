"""Model-free real-file regression for native-runner installer activation."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from v13.common import Unavailable, file_hash
from v13.runner_activation import activate_runner_candidate
from v13.bootstrap import install_llama_runner


class RunnerActivation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'bin').mkdir()
        (self.root / 'config').mkdir()
        self.binary = self.root / 'bin/llama-server'
        self.manifest = self.root / 'config/runner.json'
        self.old = self.executable('old', 0)
        self.new = self.executable('new', 0)
        self.binary.symlink_to(self.old)
        self.manifest.write_text('{"tag":"old","binary_sha256":"old"}')
        self.old_manifest = self.manifest.read_bytes()

    def executable(self, name, exit_code):
        p = self.root / name
        p.write_text('#!/bin/sh\necho ' + name + '\nexit ' + str(exit_code) + '\n')
        p.chmod(0o700)
        return p

    def activate(self, candidate=None):
        return activate_runner_candidate(candidate or self.new, self.binary, self.manifest,
                                         tag='b10964', platform='linux-x86_64')

    def test_success_publishes_exact_version_and_hash(self):
        result = self.activate()
        self.assertEqual(self.binary.resolve(), self.new)
        self.assertEqual(result, json.loads(self.manifest.read_text()))
        self.assertEqual(result['binary_sha256'], file_hash(self.new))
        self.assertEqual(result['version'], 'new')
        self.assertIsNone(result['phone_runner_proof'])
        self.assertEqual(subprocess.run([str(self.binary), '--version'], capture_output=True).returncode, 0)
        self.assertTrue(self.old.is_file())

    def test_failed_version_does_not_touch_live_or_manifest(self):
        with self.assertRaises(Unavailable):
            self.activate(self.executable('bad', 7))
        self.assertEqual(self.binary.resolve(), self.old)
        self.assertEqual(self.manifest.read_bytes(), self.old_manifest)

    def test_timeout_does_not_touch_live_or_manifest(self):
        with patch('v13.runner_activation.subprocess.run', side_effect=subprocess.TimeoutExpired('candidate', 15)):
            with self.assertRaises(Unavailable):
                self.activate()
        self.assertEqual(self.binary.resolve(), self.old)
        self.assertEqual(self.manifest.read_bytes(), self.old_manifest)

    def test_manifest_rename_failure_restores_old_symlink_and_manifest(self):
        real_replace = os.replace
        def fail_manifest(src, dst):
            if Path(dst) == self.manifest:
                raise OSError('injected manifest failure')
            return real_replace(src, dst)
        with patch('v13.runner_activation.os.replace', side_effect=fail_manifest):
            with self.assertRaises(OSError):
                self.activate()
        self.assertEqual(self.binary.resolve(), self.old)
        self.assertEqual(self.manifest.read_bytes(), self.old_manifest)
        self.assertEqual(list(self.root.rglob('*.stage-*')), [])
        self.assertEqual(list(self.root.rglob('*.backup-*')), [])

    def test_legacy_regular_binary_restored_on_manifest_failure(self):
        self.binary.unlink()
        self.binary.write_bytes(self.old.read_bytes())
        original = self.binary.read_bytes()
        real_replace = os.replace
        def fail_manifest(src, dst):
            if Path(dst) == self.manifest:
                raise OSError('injected manifest failure')
            return real_replace(src, dst)
        with patch('v13.runner_activation.os.replace', side_effect=fail_manifest):
            with self.assertRaises(OSError):
                self.activate()
        self.assertFalse(self.binary.is_symlink())
        self.assertEqual(self.binary.read_bytes(), original)
        self.assertEqual(self.manifest.read_bytes(), self.old_manifest)

    def test_no_previous_runner_remains_absent_on_manifest_failure(self):
        self.binary.unlink()
        self.manifest.unlink()
        real_replace = os.replace
        def fail_manifest(src, dst):
            if Path(dst) == self.manifest:
                raise OSError('injected manifest failure')
            return real_replace(src, dst)
        with patch('v13.runner_activation.os.replace', side_effect=fail_manifest):
            with self.assertRaises(OSError):
                self.activate()
        self.assertFalse(self.binary.exists())
        self.assertFalse(self.binary.is_symlink())
        self.assertFalse(self.manifest.exists())

    def test_manifest_symlink_refused(self):
        outside = self.root / 'external.json'
        outside.write_text('original')
        self.manifest.unlink()
        self.manifest.symlink_to(outside)
        with self.assertRaises(Unavailable):
            self.activate()
        self.assertEqual(self.binary.resolve(), self.old)
        self.assertEqual(outside.read_text(), 'original')

    def test_missing_candidate_refused(self):
        with self.assertRaises(Unavailable):
            self.activate(self.root / 'missing')
        self.assertEqual(self.binary.resolve(), self.old)

    def _install_mock(self, exit_code=0):
        original = self.old.read_bytes()
        def fake_extract(archive, dest):
            self.assertEqual(self.binary.resolve(), self.old)
            self.assertEqual(self.old.read_bytes(), original)
            self.assertNotIn(self.root / 'bin/b10964', dest.parents)
            (dest / 'release').mkdir(parents=True)
            p = dest / 'release/llama-server'
            p.write_text('#!/bin/sh\necho candidate\nexit ' + str(exit_code) + '\n')
            p.chmod(0o700)
        runner = {'runner': {'tag': 'b10964', 'linux_binaries': {'linux-x86_64': {
            'url': 'test-fixture', 'size': 1, 'sha256': 'fixture'}}}}
        with patch('v13.bootstrap.catalog', return_value=runner), \
             patch('v13.bootstrap.platform_tag', return_value='linux-x86_64'), \
             patch('v13.bootstrap.download_file', return_value=None), \
             patch('v13.bootstrap.extract', side_effect=fake_extract):
            install_llama_runner(self.root)

    def test_install_isolated_staging_preserves_old_target(self):
        self._install_mock()
        self.assertEqual(self.old.read_text(), '#!/bin/sh\necho old\nexit 0\n')
        self.assertEqual(self.binary.resolve().read_text(), '#!/bin/sh\necho candidate\nexit 0\n')
        self.assertIn('.llama-b10964-', str(self.binary.resolve()))
        self.assertEqual(json.loads(self.manifest.read_text())['binary_sha256'], file_hash(self.binary))

    def test_install_failed_candidate_cleans_stage_and_preserves_old(self):
        with self.assertRaises(Unavailable):
            self._install_mock(exit_code=9)
        self.assertEqual(self.binary.resolve(), self.old)
        self.assertEqual(self.manifest.read_bytes(), self.old_manifest)
        self.assertEqual(list((self.root / 'bin').glob('.llama-b10964-*')), [])


if __name__ == '__main__':
    unittest.main()
