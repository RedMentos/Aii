"""Synthetic adversarial type checks for A5 prompt admission; no Android claims."""
import unittest
from dataclasses import replace
from v13.percept_admission import Percept, admit


class AdmissionTypeHardening(unittest.TestCase):
    def setUp(self):
        self.good = Percept("source-1", "audio", 0, 100, "nonverbal onset", True, True)

    def test_valid_source_is_admitted(self):
        self.assertEqual(len(admit([self.good], 128).selected), 1)

    def test_invalid_source_types_rejected(self):
        for bad in (None, 3, [], {}):
            with self.subTest(bad=repr(bad)), self.assertRaises(ValueError):
                admit([replace(self.good, source_id=bad)], 128)

    def test_bool_timestamp_rejected(self):
        for field in ("start_ms", "end_ms"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                admit([replace(self.good, **{field: True})], 128)

    def test_nontext_summary_rejected(self):
        for bad in (None, 7, [], {}):
            with self.subTest(bad=repr(bad)), self.assertRaises(ValueError):
                admit([replace(self.good, summary=bad)], 128)

    def test_noninteger_priority_rejected(self):
        for bad in (True, 1.5, None, "high"):
            with self.subTest(bad=repr(bad)), self.assertRaises(ValueError):
                admit([replace(self.good, priority=bad)], 128)

    def test_unauthorized_still_excluded(self):
        self.assertEqual(admit([replace(self.good, consent=False)], 128).selected, ())


if __name__ == "__main__":
    unittest.main()
