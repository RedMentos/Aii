"""C2 Needle3 pinned Linux native control-call candidate: software-only guards."""
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import current_c2_native_linux_smoke_20261028 as probe


class CurrentC2NativeControlGuards(unittest.TestCase):
    def test_exact_current_catalog_model_binary_and_tool_pins(self):
        model, binary = probe._catalog()
        self.assertEqual(model['sha256'], probe.MODEL_SHA)
        self.assertEqual(model['size'], 35335380)
        self.assertEqual(binary['sha256'], probe.BINARY_SHA)
        self.assertEqual(binary['size'], 1246880)
        self.assertEqual(probe.TOOLS_BLOB, '954a3f468f10195fbce12d27f68585ee7edee2c9')

    def test_strict_unique_json_and_only_select_processing_route(self):
        good = b'{"function_calls":[{"name":"select_processing","arguments":{"route":"detail"}}]}'
        self.assertEqual(probe._valid_control(good), (True, 'detail'))
        self.assertEqual(probe._valid_control(
            b'{"function_calls":[{"name":"select_processing","arguments":"{\\\"route\\\":\\\"gist\\\"}"}]}'),
            (True, 'gist'))
        for raw in (
            b'hello',
            b'{"function_calls":[]}',
            b'{"function_calls":[{"name":"dangerous_tool","arguments":{"route":"detail"}}]}',
            b'{"function_calls":[{"name":"select_processing","arguments":{"route":"unknown"}}]}',
            b'{"function_calls":[],"function_calls":[]}',
            b'{"function_calls":[{"name":"select_processing","arguments":{"route":"detail"}}],"confidence":NaN}',
        ):
            self.assertEqual(probe._valid_control(raw), (False, None), raw)

    def test_synthetic_native_cli_raw_json_and_byte_hashes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cli = root / 'fake-needle'
            cli.write_text('#!/bin/sh\necho \'{"function_calls":[{"name":"select_processing","arguments":{"route":"detail"}}]}\'\n')
            cli.chmod(0o755)
            r = probe._native_one(cli, root/'model.cact', root/'tools.json',
                                  root, os.environ.copy(), timeout=3)
            raw = (root / 'C2_STDOUT_RAW.log').read_bytes()
            self.assertTrue(r['native_control_pass'])
            self.assertEqual(r['native_exit_code'], 0)
            self.assertEqual(r['proposed_route'], 'detail')
            self.assertEqual(r['stdout_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertFalse(r['raw_output_capped'])
            with self.assertRaises(FileExistsError):
                probe._native_one(cli, root/'model.cact', root/'tools.json',
                                  root, os.environ.copy(), timeout=3)

    def test_runaway_output_fails_closed_and_raw_is_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            # Execute Python as the fake CLI, which ignores fixed Needle args
            # by using a temporary executable shell wrapper.
            cli = Path(td)/'runaway'
            cli.write_text('#!/bin/sh\nexec ' + sys.executable +
                           ' -c "import os; os.write(1,b\'x\'*(2<<20))"\n')
            cli.chmod(0o755)
            r = probe._native_one(cli, Path(td)/'model', Path(td)/'tools', td,
                                  os.environ.copy(), timeout=3)
            self.assertTrue(r['raw_output_capped'])
            self.assertFalse(r['native_control_pass'])
            self.assertLessEqual(r['stdout_bytes'], probe.MAX_RAW)

    def test_timeout_and_platform_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cli = root / 'slow'
            cli.write_text('#!/bin/sh\nprintf partial\nexec sleep 2\n')
            cli.chmod(0o755)
            r = probe._native_one(cli, root/'model', root/'tools', root,
                                  os.environ.copy(), timeout=0.2)
            self.assertTrue(r['native_timed_out'])
            self.assertEqual(r['native_exit_code'], 124)
            self.assertFalse(r['native_control_pass'])
            self.assertEqual((root/'C2_STDOUT_RAW.log').read_bytes(), b'partial')
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.object(probe.platform, 'system', return_value='Windows'):
                with self.assertRaisesRegex(ValueError, 'Linux'):
                    probe.run(root/'scratch', root/'evidence')
            (root/'scratch').mkdir()
            with self.assertRaises(FileExistsError):
                probe.run(root/'scratch', root/'evidence')


if __name__ == '__main__':
    unittest.main()
