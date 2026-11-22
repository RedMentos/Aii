"""Run117CE bounded F7 Sleep scheduler diagnostic; no model/Redmi."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts import run117ce_sleep_f7_bounded_bench as m


class SleepF7Benchmark(unittest.TestCase):
    def test_invalid_bounds_rejected_before_store(self):
        for sessions, turns in ((0, 1), (257, 1), (1, 0), (1, 71),
                                (True, 1), (1, False), (1.0, 1)):
            with self.subTest(sessions=sessions, turns=turns):
                with self.assertRaisesRegex(ValueError, "BOUNDED_BENCH_INPUT_RED"):
                    m.benchmark(sessions, turns)

    def test_ten_sessions_converge_and_no_authority(self):
        r = m.benchmark(10, 1)
        self.assertEqual(r["status"], "INTEGRITY_PASS")
        self.assertEqual(r["total_turns"], 10)
        self.assertEqual(r["cycles_including_empty"], 3)
        self.assertEqual([x["sessions"] for x in r["cycle_counts"]], [8, 2, 0])
        self.assertTrue(r["closed_store_ok"])
        self.assertFalse(r["redmi_measured"])
        self.assertEqual(r["native_model_calls"], 0)
        self.assertEqual(r["learning_authority"], 0)
        self.assertFalse(r["whole_system_complete"])

    def test_standalone_cli_from_unrelated_working_directory(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "report.json"
            proc = subprocess.run(
                [sys.executable, str(Path(m.__file__).resolve()),
                 "--sessions", "1", "--turns", "1", "--out", str(out)],
                cwd=d, capture_output=True, text=True, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            report = json.loads(out.read_text())
            self.assertEqual(report["status"], "INTEGRITY_PASS")
            self.assertEqual(report["total_turns"], 1)
            self.assertFalse(report["redmi_measured"])
            self.assertEqual(len(report["script_sha256"]), 64)

    def test_nine_sessions_seventy_turns_bounded_catchup(self):
        r = m.benchmark(9, 70)
        self.assertEqual(r["total_turns"], 630)
        self.assertEqual(sum(x["turns"] for x in r["cycle_counts"]), 630)
        self.assertEqual(r["cycle_counts"][-1]["sessions"], 0)
        self.assertLessEqual(r["cycles_including_empty"], 8)
        self.assertEqual(r["jepa_weight"], 0)
        self.assertEqual(r["step2"], "UTILITY_FAIL")


if __name__ == "__main__":
    unittest.main()
