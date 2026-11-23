"""Bounded one-turn Linux subprocess capture: synthetic-only regression guards."""
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest

from scripts.native_smoke_io_20261028 import MAX_RAW_BYTES, run_one_turn


class NativeSmokeBoundedIO(unittest.TestCase):
    def test_one_turn_exit_and_raw_byte_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cli = root / 'fake-cli'
            cli.write_text("#!/bin/sh\nprintf 'Hello. synthetic response\\n[ Prompt: 1.0 t/s | Generation: 2.0 t/s ]\\n'\n")
            cli.chmod(0o755)
            r = run_one_turn([str(cli), '--single-turn'], root, 'A', os.environ.copy())
            raw = (root / 'A_STDOUT_RAW.log').read_bytes()
            self.assertEqual(r['native_exit_code'], 0)
            self.assertTrue(r['native_smoke_pass'])
            self.assertTrue(r['generation_marker_seen'])
            self.assertFalse(r['raw_output_capped'])
            self.assertEqual(r['stdout_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(r['stdout_bytes'], len(raw))
            self.assertEqual(r['raw_output_cap_bytes_per_stream'], MAX_RAW_BYTES)
            self.assertEqual((root / 'A_STDERR_RAW.log').read_bytes(), b'')
            with self.assertRaises(FileExistsError):
                run_one_turn([str(cli), '--single-turn'], root, 'A', os.environ.copy())

    def test_banner_only_not_native_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_one_turn(
                [sys.executable, '-c', 'print("llama-cli build Hello.")',
                 '--single-turn'], tmp, 'B', os.environ.copy())
            self.assertEqual(r['native_exit_code'], 0)
            self.assertFalse(r['generation_marker_seen'])
            self.assertFalse(r['native_smoke_pass'])

    def test_timeout_preserves_raw_prefix_without_false_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            cli = Path(tmp) / 'slow.sh'
            cli.write_text("#!/bin/sh\nprintf 'partial'\nexec sleep 2\n")
            cli.chmod(0o755)
            r = run_one_turn([str(cli), '--single-turn'], tmp, 'T',
                             os.environ.copy(), timeout=0.2)
            self.assertEqual(r['native_exit_code'], 124)
            self.assertTrue(r['native_timed_out'])
            self.assertFalse(r['native_smoke_pass'])
            self.assertEqual((Path(tmp) / 'T_STDOUT_RAW.log').read_bytes(), b'partial')

    def test_runaway_output_is_bounded_and_never_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_one_turn(
                [sys.executable, '-c', "import os; os.write(1,b'x'*(2<<20))",
                 '--single-turn'], tmp, 'CAP', os.environ.copy(), timeout=3)
            self.assertLessEqual(r['stdout_bytes'], MAX_RAW_BYTES)
            self.assertTrue(r['raw_output_capped'])
            self.assertFalse(r['raw_capture_complete'])
            self.assertFalse(r['native_smoke_pass'])

    def test_no_interactive_command_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'noninteractive'):
                run_one_turn(['/bin/true'], tmp, 'I', os.environ.copy())
            self.assertFalse((Path(tmp) / 'I_STDOUT_RAW.log').exists())


if __name__ == '__main__':
    unittest.main()
