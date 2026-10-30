"""Seed79 German C3 typed reader source-only preflight; no native model run."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.c3_de_native_typed_read_seed79 import (
    MODEL_SHA256, MODEL_REVISION, PINS, blob_sha, fixtures,
    parse_raw, measure, native_capture, FIXTURE, CODE,
)
from v13.agi import listarith


class GermanC3ReadPreflight(unittest.TestCase):
    def test_frozen_twelve_rows_and_original_sources(self):
        rows = fixtures()
        self.assertEqual(len(rows), 12)
        self.assertEqual(blob_sha(FIXTURE), PINS["fixture"])
        self.assertEqual(blob_sha(Path(listarith.__file__)), PINS["listarith"])
        self.assertEqual(len(set(r["id"] for r in rows)), 12)

    def test_pinned_model_and_license_provenance(self):
        model = json.loads((CODE / "specs/models.json").read_text())["models"]["language"]
        self.assertEqual(model["revision"], MODEL_REVISION)
        self.assertEqual(model["files"][0]["sha256"], MODEL_SHA256)
        self.assertEqual(model["files"][0]["size"], 219312832)
        self.assertEqual(model["license_id"], "LFM Open License 1.0")

    def test_typed_json_exact(self):
        raw = '{"values":[{"name":"Apfel","number":14},{"name":"Birne","number":26}]}'
        vals = parse_raw(raw)
        self.assertEqual(vals, fixtures()[0]["values"])
        self.assertTrue(measure(vals, fixtures()[0])["exact"])

    def test_reject_extra_or_invalid_json_types(self):
        for raw in ('{"values":[],"extra":1}', '{"values":null}',
                    '{"values":[{"name":"A","number":true}]}',
                    '{"values":[{"name":"A","number":"14"}]}',
                    '{"values":[{"name":"A","number":1,"x":2}]}'):
            with self.assertRaises(ValueError):
                parse_raw(raw)

    def test_aggregate_not_counted_as_item_but_recorded(self):
        row = fixtures()[5]
        vals = row["values"] + [{"name":"Summe","number":150}]
        score = measure(vals, row)
        self.assertTrue(score["exact"])
        self.assertEqual(score["aggregate_read"], 1)
        self.assertEqual(score["invented_nonaggregate"], 0)

    def test_duplicate_source_occurrences_counted(self):
        row = fixtures()[3]
        self.assertTrue(measure(row["values"], row)["exact"])
        bad = row["values"] + [{"name":"Extra","number":14}]
        score = measure(bad, row)
        self.assertFalse(score["exact"])
        self.assertEqual(score["invented_nonaggregate"], 1)

    def test_negative_and_positive_integer_guard(self):
        row = fixtures()[4]
        self.assertTrue(measure(row["values"], row)["exact"])
        row2 = fixtures()[9]
        self.assertTrue(measure(row2["values"], row2)["exact"])

    def test_invented_number_rejected_by_measurement(self):
        row = fixtures()[0]
        bad = [{"name":"Apfel","number":99},{"name":"Birne","number":26}]
        score = measure(bad, row)
        self.assertFalse(score["exact"])
        self.assertEqual(score["invented_nonaggregate"], 1)

    def test_no_fake_native_when_model_missing(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "home"
            out = Path(td) / "raw"
            with self.assertRaises((ValueError, FileNotFoundError, KeyError)):
                native_capture(home, out)
            self.assertFalse((out / "report.json").exists())


if __name__ == "__main__":
    unittest.main()
