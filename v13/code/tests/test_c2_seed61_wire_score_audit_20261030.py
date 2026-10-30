"""Read-only seed61 independent replay tests, original ZIPs supplied by CI."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

from scripts.c2_seed61_wire_score_audit_20261030 import (
    frozen_scorer, replay_zip, score_wire_equal, ORIGINALS,
)


class JsonWireTests(unittest.TestCase):
    def test_original_tuple_array_identity_bug(self):
        value = {"equation": {"a": {"equations": [(391, 238, 153)]}},
                 "a": True, "correct": 1}
        stored = json.loads(json.dumps(value))
        self.assertNotEqual(value, stored)
        self.assertTrue(score_wire_equal(value, stored))

    def test_numeric_change_still_rejected(self):
        value = {"equations": [(391, 238, 153)]}
        stored = json.loads(json.dumps(value))
        stored["equations"][0][2] = 154
        self.assertFalse(score_wire_equal(value, stored))

    def test_bool_int_and_float_coercion_rejected(self):
        self.assertFalse(score_wire_equal({"correct": 1}, {"correct": True}))
        self.assertFalse(score_wire_equal({"correct": 1}, {"correct": 1.0}))
        self.assertFalse(score_wire_equal({"correct": False}, {"correct": 0}))

    def test_missing_extra_fields_rejected(self):
        self.assertFalse(score_wire_equal({"a": 1}, {"a": 1, "b": 2}))
        self.assertFalse(score_wire_equal({"a": 1, "b": 2}, {"a": 1}))

    def test_nan_and_nonserializable_rejected(self):
        self.assertFalse(score_wire_equal({"a": float("nan")}, {"a": float("nan")}))
        self.assertFalse(score_wire_equal({"a": {1, 2}}, {"a": [1, 2]}))


class OriginalNativeZipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.first = os.environ.get("V13_SEED61_FIRST_ZIP")
        cls.second = os.environ.get("V13_SEED61_SECOND_ZIP")
        cls.scorer = staticmethod(frozen_scorer())

    def test_frozen_source_pins(self):
        self.assertTrue(callable(self.scorer))
        self.assertEqual(len(ORIGINALS), 2)

    def test_first_red_native_rows_and_replay(self):
        if not self.first:
            self.skipTest("Original Actions 41007813416 ZIP not supplied")
        result = replay_zip(self.first, "first", self.scorer)
        self.assertEqual(result["frozen_scorer_json_wire_exact"], "24/24")
        self.assertEqual(result["inner_sha256_verified"], 0)
        self.assertEqual(result["score_totals_original"]["D_DISTINCT_BOTH"], 1)
        self.assertEqual(result["original_workflow"], "RED")
        self.assertFalse(result["whole_system_complete"])

    def test_second_red_native_rows_manifest_and_replay(self):
        if not self.second:
            self.skipTest("Original Actions 41008162051 ZIP not supplied")
        result = replay_zip(self.second, "second", self.scorer)
        self.assertEqual(result["frozen_scorer_json_wire_exact"], "24/24")
        self.assertEqual(result["inner_sha256_verified"], 48)
        self.assertEqual(result["score_totals_original"]["C_B2_ONLY"], 6)
        self.assertEqual(result["native_c2_selected"], 4)
        self.assertEqual(result["stage_exits"]["REPORT_CHECK"], "1")
        self.assertFalse(result["step2_gate_promoted"])

    def test_changed_original_zip_refused(self):
        if not self.second:
            self.skipTest("Original Actions 41008162051 ZIP not supplied")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tampered.zip"
            path.write_bytes(Path(self.second).read_bytes() + b"\x00")
            with self.assertRaisesRegex(ValueError, "ORIGINAL_ZIP_SHA256_CHANGED"):
                replay_zip(path, "second", self.scorer)


if __name__ == "__main__":
    unittest.main()
