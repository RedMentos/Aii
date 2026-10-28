"""No native model execution here: deterministic smoke runner control tests."""
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from scripts.step2_current_catalog_native_smoke import (
    CONTEXT, PROMPT, SEED, THREADS, TOKENS, _run, command, locate_cli, preflight,
)


def archive(path, members):
    with tarfile.open(path, 'w:gz') as tf:
        for name in members:
            data = b'#!/bin/sh\necho synthetic\n'
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))


class NativeSmokeControls(unittest.TestCase):
    def test_command_is_fixed_small_deterministic_smoke(self):
        argv = command('/runner/llama-cli', '/models/body.gguf')
        self.assertEqual(argv[:2], ['/runner/llama-cli', '-m'])
        self.assertIn(PROMPT, argv)
        self.assertEqual(argv[argv.index('--seed') + 1], str(SEED))
        self.assertEqual(argv[argv.index('-n') + 1], str(TOKENS))
        self.assertEqual(argv[argv.index('-c') + 1], str(CONTEXT))
        self.assertEqual(argv[argv.index('-t') + 1], str(THREADS))

    def test_safe_cli_member_located_without_executing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / 'runner.tar.gz'
            archive(path, ['pkg/bin/llama-cli', 'pkg/LICENSE'])
            cli = locate_cli(path, root / 'extract')
            self.assertTrue(cli.is_file())
            self.assertEqual(cli.name, 'llama-cli')

    def test_duplicate_cli_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / 'runner.tar.gz'
            archive(path, ['a/llama-cli', 'b/llama-cli'])
            with self.assertRaises(RuntimeError):
                locate_cli(path, root / 'extract')

    def test_unsafe_tar_member_rejected_before_extract(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / 'runner.tar.gz'
            archive(path, ['../escape', 'pkg/llama-cli'])
            with self.assertRaises(ValueError):
                locate_cli(path, root / 'extract')
            self.assertFalse((root / 'escape').exists())

    def test_bounded_subprocess_result(self):
        r = _run(['/bin/echo', 'synthetic'], 3, {})
        self.assertEqual(r['returncode'], 0)
        self.assertFalse(r['timeout'])
        self.assertIn(b'synthetic', r['stdout'])
        t = _run(['/bin/sleep', '1'], 0.01, {})
        self.assertTrue(t['timeout'])

    def test_low_cgroup_memory_refuses_before_download(self):
        with tempfile.TemporaryDirectory() as td:
            with patch('scripts.step2_current_catalog_native_smoke.cgroup_memory_limit',
                       return_value=1024):
                with self.assertRaises(RuntimeError):
                    preflight(Path(td) / 'new-scratch')


if __name__ == '__main__':
    unittest.main()
