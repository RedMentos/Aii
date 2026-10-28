"""Current B1/B2 distinct native Linux smoke: pinned source and serial subprocess guards."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import current_b1b2_native_linux_smoke_20261028 as probe


class CurrentB1B2NativeGuards(unittest.TestCase):
    def test_catalog_exact_distinct_weights_and_licenses(self):
        entries, runner = probe._catalog()
        self.assertEqual([x[0] for x in entries], ['B1_DETAIL', 'B2_GIST'])
        self.assertNotEqual(entries[0][2]['sha256'], entries[1][2]['sha256'])
        self.assertEqual([x[1]['size'] for x in entries], [695755488, 563036064])
        self.assertEqual([x[1]['license_id'] for x in entries],
                         ['LFM Open License 1.0', 'Apache-2.0'])
        self.assertEqual(runner['sha256'],
                         '9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443')

    def test_native_one_real_bounded_subprocess_and_raw_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cli = root / 'llama-cli'
            cli.write_text('#!/bin/sh\necho Hello. generated-synthetic-tokens\necho "[ Prompt: 1 t/s | Generation: 2 t/s ]"\n')
            cli.chmod(0o755)
            result = probe._native_one(cli, root/'fake.gguf', 'B1_DETAIL', root, {})
            self.assertEqual(result['native_exit_code'], 0)
            self.assertTrue(result['native_smoke_pass'])
            self.assertIn('generated-synthetic', (root/'B1_DETAIL_STDOUT_RAW.log').read_text())
            self.assertTrue((root/'B1_DETAIL_STDERR_RAW.log').exists())

    def test_timeout_keeps_partial_raw_and_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(probe.subprocess, 'run',
                              side_effect=subprocess.TimeoutExpired(
                                  cmd=['llama-cli'], timeout=180,
                                  output=b'Hello. partial', stderr=b'timeout')):
                result = probe._native_one(root/'cli', root/'model', 'B2_GIST', root, {})
            self.assertEqual(result['native_exit_code'], 124)
            self.assertFalse(result['native_smoke_pass'])
            self.assertTrue((root/'B2_GIST_STDOUT_RAW.log').exists())
            self.assertTrue(result['native_timed_out'])

    def test_no_download_on_invalid_platform_or_existing_scratch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(probe.platform, 'system', return_value='Windows'):
                with self.assertRaisesRegex(ValueError, 'Linux'):
                    probe.run(root/'scratch', root/'evidence')
            (root/'scratch').mkdir()
            with self.assertRaises(FileExistsError):
                probe.run(root/'scratch', root/'evidence')


if __name__ == '__main__':
    unittest.main()
