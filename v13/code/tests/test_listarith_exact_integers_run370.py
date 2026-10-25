"""Run370 RED-first: R4 typed model values must not be coerced into integers.

No native model, permission change, cohort change or age promotion.
"""
import json
import threading
import unittest

from v13.agi import listarith as L


TEXT = "A: 1. B: 9. What is the total?"
GOOD = [{"name": "A", "number": 1}, {"name": "B", "number": 9}]


class FakeReader:
    def __init__(self, values):
        self.values = values

    def generate(self, *args, **kwargs):
        yield json.dumps({"values": self.values})


class ExactIntegerRun370(unittest.TestCase):
    def test_valid_exact_integers_still_work(self):
        self.assertEqual(L.compute("total", GOOD, TEXT)[0], 10)
        self.assertEqual(L.encode(GOOD), "A=1\nB=9")
        self.assertEqual(L.read_values(FakeReader(GOOD), TEXT, threading.Event(), None), GOOD)
        negative = "A: -1. B: 9. What is the total?"
        self.assertEqual(L.compute("total", [{"name": "A", "number": -1}, GOOD[1]], negative)[0], 8)

    def test_untrusted_numeric_coercions_rejected_at_all_three_boundaries(self):
        for bad in (True, False, 1.8, 1.0, "1", "01", None):
            rows = [{"name": "A", "number": bad}, GOOD[1]]
            with self.subTest(value=repr(bad), boundary="compute"):
                with self.assertRaises(ValueError):
                    L.compute("total", rows, TEXT)
            with self.subTest(value=repr(bad), boundary="encode"):
                with self.assertRaises(ValueError):
                    L.encode(rows)
            with self.subTest(value=repr(bad), boundary="read"):
                with self.assertRaises(ValueError):
                    L.read_values(FakeReader(rows), TEXT, threading.Event(), None)

    def test_reader_rejects_non_object_and_missing_number(self):
        for rows in ([1, GOOD[1]], [{"name": "A"}, GOOD[1]], [{"name": 2, "number": 1}, GOOD[1]]):
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):
                    L.read_values(FakeReader(rows), TEXT, threading.Event(), None)

    def test_original_number_guard_and_aggregate_exclusion_remain(self):
        self.assertEqual(L.compute("total", GOOD + [{"name": "Total", "number": 10}], TEXT)[0], 10)
        with self.assertRaisesRegex(ValueError, "number not in"):
            L.compute("total", [{"name": "A", "number": 7}, GOOD[1]], TEXT)
        with self.assertRaisesRegex(ValueError, "number not in"):
            L.compute("total", [{"name": "A", "number": 1}, {"name": "B", "number": 1}], TEXT)


if __name__ == "__main__":
    unittest.main()
