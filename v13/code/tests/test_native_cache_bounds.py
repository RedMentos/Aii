"""G6B: every llama-server start carries bounded host-cache/checkpoint flags.

Real child on a loopback fixture; no model inference. The memory effect itself
is measured separately (docs/proofs/continuation-20261012/native-cache-bounds/).
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from v13.config import DEFAULTS, validate
from v13.runners import LlamaRunner, native_cache_args


class NativeCacheBounds(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.home = Path(self.tmp.name)
        for d in ('bin', 'logs', 'config'):
            (self.home/d).mkdir()
        self.model = self.home/'model.gguf'; self.model.write_bytes(b'software-model-fixture')
        script = '#!'+sys.executable+'''\nimport sys
from http.server import BaseHTTPRequestHandler,HTTPServer
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        self.send_response(200);self.end_headers();self.wfile.write(b'{"status":"ok"}')
HTTPServer(('127.0.0.1',int(sys.argv[sys.argv.index('--port')+1])),Handler).serve_forever()
'''
        binary = self.home/'bin/llama-server'; binary.write_text(script); binary.chmod(0o755)
        self.environment = patch.dict(os.environ, {}, clear=False); self.environment.start()
        os.environ.pop('V13_LLAMA_SERVER', None); os.environ.pop('V13_MEMORY_FILE', None)
        self.runner = None

    def tearDown(self):
        if self.runner:
            self.runner.unload()
        self.environment.stop(); self.tmp.cleanup()

    def launched(self, cfg, purpose='generate'):
        self.runner = LlamaRunner(self.home, 'B2_BODY', self.model, cfg, purpose=purpose)
        real = subprocess.Popen
        with patch('v13.runners.subprocess.Popen', wraps=real) as popen:
            self.runner.load(threading.Event(), time.monotonic()+4)
        return popen.call_args.args[0]

    def flag(self, cmd, name):
        self.assertEqual(cmd.count(name), 1)
        return cmd[cmd.index(name)+1]

    def test_defaults_bound_both_flags_for_every_purpose(self):
        for purpose in ('generate', 'tap', 'embed'):
            cmd = self.launched({'context_tokens': 256, 'threads': 1}, purpose)
            self.assertEqual(self.flag(cmd, '--cache-ram'), str(DEFAULTS['native_cache_ram_mb']))
            self.assertEqual(self.flag(cmd, '--ctx-checkpoints'), str(DEFAULTS['native_ctx_checkpoints']))
            self.runner.unload(); self.runner = None

    def test_configured_values_including_zero_reach_the_child(self):
        cmd = self.launched({'context_tokens': 256, 'threads': 1, 'native_cache_ram_mb': 0, 'native_ctx_checkpoints': 0})
        self.assertEqual(self.flag(cmd, '--cache-ram'), '0')
        self.assertEqual(self.flag(cmd, '--ctx-checkpoints'), '0')

    def test_defaults_stay_inside_a_256_mib_body_budget(self):
        # Largest measured checkpoint: Qwen3.5-0.8B 19.3 MiB (docs/NATIVE_CACHE.md).
        worst = DEFAULTS['native_cache_ram_mb'] + DEFAULTS['native_ctx_checkpoints']*19.3
        self.assertLessEqual(worst, 256)
        self.assertEqual(native_cache_args({}), ['--cache-ram', '128', '--ctx-checkpoints', '6'])

    def test_out_of_range_values_are_rejected(self):
        for key, value in (('native_cache_ram_mb', 9000), ('native_ctx_checkpoints', 33), ('native_cache_ram_mb', -1)):
            with self.assertRaises(ValueError):
                validate(dict(DEFAULTS, **{key: value}))


if __name__ == '__main__':
    unittest.main()
