"""WP-T14 review: preserve canonical runtime stage order when reading persisted timing marks."""
import json
import unittest
from v13 import control_budget as cb

class _Store:
    def __init__(self, rows):
        self._rows = rows
    def rows(self, sql, args=()):
        return self._rows

def _row(marks, created):
    return {"metadata": json.dumps({"stage_marks_s": marks}), "created": created}

class StageOrderReview(unittest.TestCase):
    def test_reversed_known_stages_rejected(self):
        marks = {"ingress": 0., "routing": .5, "preanswer_observers": .3, "finished": 1.}
        self.assertEqual(cb.durations(marks), {})

    def test_reversed_row_excluded_from_denominator(self):
        invalid = {"ingress": 0., "routing": .5, "preanswer_observers": .3, "finished": 1.}
        valid = {"ingress": 0., "routing": .2, "finished": 1.}
        result = cb.latency(_Store([_row(invalid, 90.), _row(valid, 100.)]))
        self.assertEqual(result["turns"], 1)
        self.assertEqual(result["control_p95_ms"], 1000.)
        self.assertEqual(result["inline_observer_rate"], 0.)
        self.assertIsNone(result["turns_per_hour"])
        json.dumps(result, allow_nan=False)

    def test_sparse_ordered_and_equal_marks_remain_valid(self):
        sparse = {"ingress": 0., "routing": .2, "finished": 1.}
        self.assertEqual(cb.durations(sparse), {"ingress": .2, "routing": .8})
        equal = {"ingress": 0., "routing": .2, "preanswer_observers": .2, "finished": 1.}
        self.assertEqual(cb.durations(equal), {
            "ingress": .2, "routing": 0., "preanswer_observers": .8
        })
        self.assertEqual(cb.durations({"ingress": 0., "unknown": float("nan"), "finished": 1.}), {"ingress": 1.})

if __name__ == "__main__":
    unittest.main()
