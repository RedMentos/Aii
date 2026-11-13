"""Offline contract checks for synthetic A5 -> B/C benchmark; not Redmi proof."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bench_audio_shadow_route.py"
spec = importlib.util.spec_from_file_location("bench_audio_shadow_route", SCRIPT)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


class AudioShadowBenchmarkTests(unittest.TestCase):
    def test_one_and_three_iterations_recheck_source(self):
        for n in (1, 3):
            with self.subTest(n=n):
                result = bench.run(n)
                self.assertEqual(result["source_rechecks"], n)
                self.assertEqual(result["iterations"], n)
                self.assertEqual(result["evidence"], "SYNTHETIC_HOST_ONLY")
                self.assertFalse(result["android_verified"])
                self.assertFalse(result["native_audio"])
                self.assertGreaterEqual(result["median_ms"], 0)
                self.assertGreaterEqual(result["tracemalloc_peak_bytes"], 0)

    def test_iteration_budget(self):
        for n in (0, -1, 100001):
            with self.subTest(n=n), self.assertRaises(ValueError):
                bench.run(n)


if __name__ == "__main__":
    unittest.main()
