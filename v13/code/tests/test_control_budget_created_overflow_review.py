"""WP-T14 review: malformed persisted created timestamps must not crash control reporting."""
import json
import math
import unittest
from v13 import control_budget as cb

MARKS = {"ingress": 0., "routing": .2, "finished": 1.}

class _Store:
    def __init__(self, rows):
        self._rows = rows
    def rows(self, sql, args=()):
        return self._rows

def _row(created):
    return {"metadata": json.dumps({"stage_marks_s": MARKS}), "created": created}

class CreatedOverflowReview(unittest.TestCase):
    def test_oversized_int_is_excluded_without_crashing_valid_row(self):
        report = cb.latency(_Store([_row(10**1000), _row(100.)]))
        self.assertEqual(report["turns"], 1)
        self.assertEqual(report["control_p95_ms"], 1000.)
        self.assertIsNone(report["turns_per_hour"])
        json.dumps(report, allow_nan=False)

    def test_oversized_int_only_returns_empty_evidence(self):
        report = cb.latency(_Store([_row(10**1000)]))
        self.assertEqual(report["turns"], 0)
        self.assertIsNone(report["control_p95_ms"])
        self.assertIsNone(report["turns_per_hour"])
        json.dumps(report, allow_nan=False)

    def test_valid_int_and_float_timestamps_remain_accepted(self):
        report = cb.latency(_Store([_row(100), _row(110.)]))
        self.assertEqual(report["turns"], 2)
        self.assertEqual(report["control_p95_ms"], 1000.)
        self.assertTrue(math.isfinite(report["turns_per_hour"]))

if __name__ == "__main__":
    unittest.main()
