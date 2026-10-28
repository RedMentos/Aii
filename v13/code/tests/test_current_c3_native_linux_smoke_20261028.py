"""Pinned current-catalog C3 Linux native smoke: software guard tests only."""
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from scripts import current_c3_native_linux_smoke_20261028 as probe


def make_tar(path, name, body=b'#!/bin/sh\necho synthetic\n'):
    with tarfile.open(path, 'w:gz') as archive:
        info = tarfile.TarInfo(name)
        info.mode = 0o755
        info.size = len(body)
        archive.addfile(info, io.BytesIO(body))


class CurrentC3NativeSmokeGuards(unittest.TestCase):
    def test_current_catalog_exact_immutable_pins(self):
        model, file, binary = probe._catalog()
        self.assertEqual(model['license_id'], 'LFM Open License 1.0')
        self.assertEqual(file['sha256'], probe.MODEL_SHA)
        self.assertEqual(file['size'], probe.MODEL_BYTES)
        self.assertEqual(binary['sha256'], probe.RUNNER_SHA)
        self.assertEqual(binary['size'], probe.RUNNER_BYTES)

    def test_safe_extraction_requires_one_executable_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'safe.tar.gz'
            make_tar(archive, 'llama-b10964/build/bin/llama-cli')
            cli = probe._extract_runner(archive, root / 'extracted')
            self.assertTrue(cli.is_file())
            self.assertTrue(cli.name == 'llama-cli')
            self.assertTrue(cli.stat().st_mode & 0o111)
            with self.assertRaises(FileExistsError):
                probe._extract_runner(archive, root / 'extracted')

    def test_unsafe_traversal_and_missing_executable_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'bad.tar.gz'
            make_tar(archive, '../escape')
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                probe._extract_runner(archive, root / 'out')
            self.assertFalse((root / 'escape').exists())
            make_tar(archive, 'safe/readme.txt')
            with self.assertRaisesRegex(ValueError, 'one executable'):
                probe._extract_runner(archive, root / 'out2')

    def test_no_download_when_platform_or_destination_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(probe.platform, 'system', return_value='Windows'):
                with self.assertRaisesRegex(ValueError, 'Linux'):
                    probe.run(root / 'scratch', root / 'evidence')
            (root / 'scratch').mkdir()
            with self.assertRaises(FileExistsError):
                probe.run(root / 'scratch', root / 'evidence')


if __name__ == '__main__':
    unittest.main()
