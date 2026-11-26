"""Local contract tests for the native MoE benchmark RAM admission gate."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import moe_resource_gate as G


class ProcParsingTests(unittest.TestCase):
    def test_memavailable_kib_to_mib(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "meminfo"
            p.write_text("MemTotal:       6000000 kB\nMemFree: 1000 kB\nMemAvailable: 1024000 kB\n")
            self.assertEqual(G.read_memavailable_mib(p), 1000.0)

    def test_missing_or_malformed_memavailable_is_unmeasured(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "meminfo"
            p.write_text("MemTotal: 6000000 kB\n")
            self.assertIsNone(G.read_memavailable_mib(p))
            p.write_text("MemAvailable: nope kB\n")
            self.assertIsNone(G.read_memavailable_mib(p))
            p.write_text("MemAvailable: 12 MB\n")
            self.assertIsNone(G.read_memavailable_mib(p))

    def test_current_host_proc_metrics_are_readable(self):
        self.assertGreater(G.read_memavailable_mib(), 0)
        self.assertGreater(G.read_vmhwm_mib(os.getpid()), 0)

    def test_vmhwm_reads_process_high_water(self):
        with tempfile.TemporaryDirectory() as td:
            status = Path(td) / "123" / "status"
            status.parent.mkdir()
            status.write_text("Name:\ttest\nVmRSS:\t1024 kB\nVmHWM:\t2048 kB\n")
            self.assertEqual(G.read_vmhwm_mib(123, td), 2.0)
            self.assertIsNone(G.read_vmhwm_mib(124, td))


class PairAdmissionTests(unittest.TestCase):
    def test_exact_budget_is_admitted(self):
        r = G.pair_memory_admission([700, 600], available_mib=2324, reserve_mib=1024)
        self.assertEqual(r["status"], "ADMITTED")
        self.assertEqual(r["required_mib"], 2324)
        self.assertEqual(r["headroom_after_required_mib"], 0)

    def test_one_mib_below_budget_is_blocked(self):
        r = G.pair_memory_admission([700, 600], available_mib=2323, reserve_mib=1024)
        self.assertEqual(r["status"], "BLOCKED_INSUFFICIENT_MEMORY")

    def test_missing_peak_never_becomes_zero(self):
        for missing in (None, 0, -1, float("nan"), float("inf")):
            r = G.pair_memory_admission([700, missing], available_mib=5000)
            self.assertEqual(r["status"], "BLOCKED_UNMEASURED_SINGLE_RUN_PEAK")

    def test_missing_memavailable_fails_closed(self):
        r = G.pair_memory_admission([700, 600], available_mib=None)
        self.assertEqual(r["status"], "BLOCKED_MEMAVAILABLE_UNAVAILABLE")

    def test_pair_requires_two_bodies(self):
        r = G.pair_memory_admission([700], available_mib=5000)
        self.assertEqual(r["status"], "BLOCKED_NEEDS_TWO_MEASURED_BODIES")

    def test_invalid_reserve_rejected(self):
        with self.assertRaises(ValueError):
            G.pair_memory_admission([700, 600], available_mib=5000, reserve_mib=-1)


if __name__ == "__main__":
    unittest.main()
