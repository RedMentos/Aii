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
        self.assertIn('--single-turn', argv)

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

    def test_three_roles_synthetic_serial_smoke_preserves_legacy_and_bounded_raw(self):
        # Synthetic shell CLI only. This test does NOT constitute native model proof.
        from scripts import step2_current_catalog_native_smoke as probe
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scratch = root / 'scratch'
            evidence = root / 'evidence'

            class FakeManager:
                def __init__(self, home):
                    self.home = Path(home)

                def path_for(self, role):
                    return self.home / (role + '.gguf')

            def fake_models(home, report, blob, progress):
                home.mkdir(parents=True)
                for role in probe.ROLES:
                    (home / (role + '.gguf')).write_bytes(b'GGUF synthetic ' + role.encode())
                report.write_text('{}')
                return {}

            def fake_runner(home, report, blob, progress):
                home.mkdir(parents=True)
                cli = (b'#!/bin/sh\n'
                       b'if [ "$1" = "--version" ]; then echo synthetic-version; exit 0; fi\n'
                       b'echo Hello. synthetic-answer\n'
                       b'echo "[ Prompt: 1 t/s | Generation: 2 t/s ]"\n')
                with tarfile.open(home / 'binary.tar.gz', 'w:gz') as tf:
                    info = tarfile.TarInfo('pkg/bin/llama-cli')
                    info.size = len(cli)
                    info.mode = 0o755
                    tf.addfile(info, io.BytesIO(cli))
                report.write_text('{}')
                return {}

            with (patch.object(probe, 'preflight'),
                  patch.object(probe, 'model_probe', side_effect=fake_models),
                  patch.object(probe, 'runner_probe', side_effect=fake_runner),
                  patch.object(probe, 'ModelManager', FakeManager)):
                report = probe.smoke(scratch, evidence, 'synthetic-blob')
            self.assertEqual(len(report['roles']), 3)
            self.assertTrue(report['native_linux_load_decode'])
            for role, row in zip(probe.ROLES, report['roles']):
                self.assertEqual(row['role'], role)
                self.assertTrue(row['native_smoke_pass'])
                self.assertTrue(row['generation_marker_seen'])
                self.assertTrue(row['raw_capture_complete'])
                self.assertFalse(row['raw_output_capped'])
                self.assertEqual((evidence / (role + '.stdout')).read_bytes(),
                                 (evidence / (role + '_STDOUT_RAW.log')).read_bytes())
                self.assertEqual((evidence / (role + '.stderr')).read_bytes(),
                                 (evidence / (role + '_STDERR_RAW.log')).read_bytes())
                self.assertTrue((evidence / (role + '.json')).is_file())

    def test_low_cgroup_memory_refuses_before_download(self):
        with tempfile.TemporaryDirectory() as td:
            with patch('scripts.step2_current_catalog_native_smoke.cgroup_memory_limit',
                       return_value=1024):
                with self.assertRaises(RuntimeError):
                    preflight(Path(td) / 'new-scratch')


if __name__ == '__main__':
    unittest.main()
