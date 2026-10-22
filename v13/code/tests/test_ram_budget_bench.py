"""RAM budget bench: the measured command line must be the runtime's command line.

Offline: a loopback fixture stands in for llama-server; no model inference.
The measurements themselves live in bench-results/ram-budget-20261012/.
"""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from v13.config import DEFAULTS
from v13.runners import LlamaRunner

APP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ram_budget_bench', APP/'scripts/ram_budget_bench.py')
bench = importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)


class RamBudgetBench(unittest.TestCase):
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
        self.binary = self.home/'bin/llama-server'; self.binary.write_text(script); self.binary.chmod(0o755)
        self.environment = patch.dict(os.environ, {}, clear=False); self.environment.start()
        for k in ('V13_LLAMA_SERVER', 'V13_MEMORY_FILE'):
            os.environ.pop(k, None)

    def tearDown(self):
        self.environment.stop(); self.tmp.cleanup()

    def runtime_cmd(self, role, purpose):
        cfg = {k: DEFAULTS[k] for k in bench.RUNNER_DEFAULTS}
        runner = LlamaRunner(self.home, role, self.model, cfg, purpose=purpose)
        try:
            with patch('v13.runners.subprocess.Popen', wraps=subprocess.Popen) as popen:
                runner.load(threading.Event(), time.monotonic()+4)
            return popen.call_args.args[0]
        finally:
            runner.unload()

    @staticmethod
    def without_port(cmd):
        cmd = list(cmd); i = cmd.index('--port'); del cmd[i:i+2]; return cmd[1:]

    def test_defaults_are_the_runtime_defaults(self):
        for k, v in bench.RUNNER_DEFAULTS.items():
            self.assertEqual(DEFAULTS[k], v, k)

    def test_command_line_matches_llama_runner_for_every_purpose(self):
        for role, purpose in (('C3_LANGUAGE', 'generate'), ('B1_DETAIL', 'generate'), ('C3_LANGUAGE', 'tap'),
                              ('B2_GIST', 'tap'), ('EMBED', 'embed')):
            server = bench.Server(str(self.binary), self.model, purpose, role); server.port = 1
            self.assertEqual(self.without_port(server.cmd()), self.without_port(self.runtime_cmd(role, purpose)), (role, purpose))

    def test_variant_flags_are_appended_after_runtime_flags(self):
        server = bench.Server(str(self.binary), self.model, 'generate', 'B1_DETAIL', ['-c', '1024']); server.port = 1
        cmd = server.cmd()
        self.assertEqual(cmd[-2:], ['-c', '1024']); self.assertEqual(cmd.count('-c'), 2)

    def test_smaps_reads_own_process(self):
        s = bench.smaps(os.getpid())
        if s is None:
            self.skipTest('no smaps_rollup on this kernel')
        self.assertGreater(s['Rss'], 0); self.assertIn('Pss_Anon', s); self.assertIn('VmHWM', s)
        self.assertIsNone(bench.smaps(2**22+1))

    def test_plan_covers_slots_variants_and_combos(self):
        args = type('A', (), {'scenarios': {'single', 'variants', 'combo'}, 'quant_dir': None})()
        names = [n for n, _, _ in bench.plan(args, bench.model_paths(self.home))]
        for r in ('C3_LANGUAGE', 'B1_DETAIL', 'B2_GIST', 'EMBED', 'C3_TAP'):
            self.assertIn('single:'+r, names)
        self.assertIn('variant:B1_DETAIL:no-repack', names)
        self.assertIn('combo:C3+B1+B2 resident', names)
        seq = [s for n, _, s in bench.plan(args, bench.model_paths(self.home)) if 'sequential' in n]
        self.assertTrue(seq and all(seq))

    def test_canon_budget_is_section_73(self):
        # §73: weight_hot <= 2.0 GB, total soft <= 3.4 GB, hard backoff 3.8 GB
        self.assertEqual(bench.CANON_BUDGET_MB, {'weight_hot_max': 2048, 'total_rss_soft_max': 3482, 'total_rss_hard_backoff': 3891})


if __name__ == '__main__':
    unittest.main()
