"""Regression: a procedural shortcut cannot become READY without latency evidence."""
import math
import unittest
from v13.fastforward import FastForward


class MemoryStore:
    def __init__(self):
        self.data = None
        self.version = 0

    def state(self, key, default=None):
        return self.data, self.version

    def set_state(self, key, value, expected=None):
        if expected != self.version:
            raise ValueError("stale")
        self.data = value
        self.version += 1


class ProceduralLatencyGateTest(unittest.TestCase):
    def _run(self, predicted):
        f = FastForward(MemoryStore())
        for _ in range(5):
            f.record_turn("stable", "both", "FINAL", 8.0)
        self.assertEqual(f.procedural("stable")["stage"], "SHADOW")
        for _ in range(10):
            f.record_turn("stable", "both", "FINAL", 8.0,
                          predicted_fast_s=predicted)
        return f.procedural("stable")["stage"]

    def test_missing_latency_does_not_promote(self):
        self.assertEqual(self._run(None), "SHADOW")

    def test_nonfinite_latency_does_not_promote(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                self.assertEqual(self._run(value), "SHADOW")

    def test_slower_or_negative_latency_does_not_promote(self):
        self.assertEqual(self._run(9.0), "SHADOW")
        self.assertEqual(self._run(-1.0), "SHADOW")

    def test_measured_noninferior_latency_promotes(self):
        self.assertEqual(self._run(7.0), "READY")


if __name__ == "__main__":
    unittest.main()
