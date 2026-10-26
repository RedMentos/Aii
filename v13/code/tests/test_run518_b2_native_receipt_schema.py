"""Run518: reject-quote count schema from actual Run515 native, no model."""
import tempfile
from pathlib import Path
import unittest

from tests.test_run513_b2_receipt_postflight import make_stage, update_rows
from scripts.run513_b2_receipt_postflight import audit


class NativeReceiptRejectedQuoteCount(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.rows, _ = make_stage(self.work)

    def test_actual_native_integer_zero_schema_is_valid(self):
        self.assertEqual(self.rows[0]["rejected_quotes"], 0)
        report, reduced = audit(self.work, 0)
        self.assertEqual(report["source_bound_rows"], 12)
        self.assertEqual(len(reduced), 12)
        self.assertFalse(report["native_execution_independently_confirmed"])

    def test_invalid_type_negative_and_impossible_count_fail(self):
        for invalid in ([], False, 0.0, -1, 2, "0", None):
            with self.subTest(invalid=invalid):
                self.rows[0]["rejected_quotes"] = invalid
                update_rows(self.work, self.rows)
                with self.assertRaisesRegex(ValueError, "NATIVE_ROW_LIFECYCLE_DRIFT"):
                    audit(self.work, 0)
        self.rows[0]["rejected_quotes"] = 0
        update_rows(self.work, self.rows)
        self.assertEqual(audit(self.work, 0)[0]["source_bound_rows"], 12)


if __name__ == "__main__":
    unittest.main()
