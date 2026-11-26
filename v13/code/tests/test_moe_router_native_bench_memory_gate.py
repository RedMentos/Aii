"""Integration tests for the native benchmark's concurrent-pair admission."""
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "moe_router_native_bench.py"


def load_bench():
    monitor = types.ModuleType("moe_router_monitor")
    bench = types.ModuleType("moe_router_bench")
    bench.OLD_EN = ["en"]
    bench.OLD_DE = ["de"]
    bench.PREAMBLES = ["", "p1", "p2"]
    old_monitor = sys.modules.get("moe_router_monitor")
    old_bench = sys.modules.get("moe_router_bench")
    sys.modules["moe_router_monitor"] = monitor
    sys.modules["moe_router_bench"] = bench
    try:
        spec = importlib.util.spec_from_file_location("moe_router_native_bench_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if old_monitor is None:
            sys.modules.pop("moe_router_monitor", None)
        else:
            sys.modules["moe_router_monitor"] = old_monitor
        if old_bench is None:
            sys.modules.pop("moe_router_bench", None)
        else:
            sys.modules["moe_router_bench"] = old_bench


class PairGateIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_bench()

    def _run_main(self, available_mib):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        out = root / "result.json"
        argv = [
            "moe_router_native_bench.py",
            "--body", "B1:tokenizer:2:ffn_norm:Q4=/model-b1.gguf",
            "--body", "B2:tokenizer:2:ffn_norm:Q4=/model-b2.gguf",
            "--tap", "/fake/tap", "--work", str(root / "work"), "--out", str(out), "--pair",
            "--pair-reserve-mib", "1024",
        ]
        with patch.object(self.mod, "write_ids", return_value=[{"preamble": 0, "n_text": 1}] * 3), \
             patch.object(self.mod, "calib_and_p0", return_value=({"thresholds": {}}, {0: object()})), \
             patch.object(self.mod, "run_tap", return_value={"vmhwm_mb": 700.0, "vmhwm_status": "MEASURED"}) as run_tap, \
             patch.object(self.mod, "read_memavailable_mib", return_value=available_mib), \
             patch.object(sys, "argv", argv):
            self.mod.main()
        return json.loads(out.read_text()), run_tap.call_count

    def test_run_tap_measures_real_proc_vmhwm_for_child(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fake = root / "fake_tap.py"
            fake.write_text("#!/usr/bin/env python3\nimport time\npayload = bytearray(24 * 1024 * 1024)\ntime.sleep(0.3)\n")
            fake.chmod(0o700)
            result = self.mod.run_tap(str(fake), "unused.gguf", root / "ids.jsonl", root / "tap-out", 1)
            self.assertEqual(result["vmhwm_status"], "MEASURED")
            self.assertGreater(result["vmhwm_mb"], 16.0)
            self.assertGreater(result["memavailable_before_mib"], 0)

    def test_insufficient_memory_skips_concurrent_processes(self):
        result, calls = self._run_main(2323.0)
        self.assertEqual(result["pair"]["status"], "SKIPPED_RESOURCE_GATE")
        self.assertEqual(result["pair"]["admission"]["status"], "BLOCKED_INSUFFICIENT_MEMORY")
        self.assertEqual(calls, 2)

    def test_sufficient_memory_allows_pair_after_measured_singles(self):
        result, calls = self._run_main(3000.0)
        self.assertEqual(result["pair"]["status"], "RAN")
        self.assertEqual(result["pair"]["admission"]["status"], "ADMITTED")
        self.assertEqual(result["pair"]["sum_vmhwm_mb"], 1400.0)
        self.assertEqual(calls, 4)


if __name__ == "__main__":
    unittest.main()
