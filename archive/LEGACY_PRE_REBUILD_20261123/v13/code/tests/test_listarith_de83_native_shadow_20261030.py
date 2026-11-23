"""Source-only prereg seed83 pilot tests; no native model execution."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.listarith_de83_native_shadow import (
    BINARY_SHA256, CODE, FIXTURE, MODEL_REVISION, MODEL_SHA256,
    PINS, blob_sha, fixtures, invented_numbers, native_capture, outcome, score,
)
from v13.agi import listarith
from v13.agi import listarith_de_shadow_pipeline as pipeline


def shadow(status, op=None, value=None):
    return {"status": status, "operation": op, "value": value}


class NativeGerman83Preflight(unittest.TestCase):
    def test_frozen_rows_and_source_pins(self):
        rows = fixtures()
        self.assertEqual(len(rows), 24)
        self.assertEqual(blob_sha(FIXTURE), PINS["fixture"])
        self.assertEqual(blob_sha(Path(pipeline.__file__)), PINS["pipeline"])
        self.assertEqual(blob_sha(Path(listarith.__file__)), PINS["listarith"])
        self.assertEqual(len({r["text"] for r in rows}), 24)
        self.assertEqual([sum(r["expected_operation"] == k for r in rows)
                          for k in ("total", "difference_max_min", None)],
                         [12, 4, 8])

    def test_disjoint_from_seed79(self):
        rows = fixtures()
        prior = json.loads((CODE / "specs/c3_de_native_typed_read_seed79.json").read_text())
        self.assertFalse({r["text"] for r in rows} & {r["text"] for r in prior["rows"]})

    def test_model_and_binary_pins(self):
        model = json.loads((CODE / "specs/models.json").read_text())["models"]["language"]
        self.assertEqual(model["revision"], MODEL_REVISION)
        self.assertEqual(model["files"][0]["sha256"], MODEL_SHA256)
        self.assertEqual(model["license_id"], "LFM Open License 1.0")
        self.assertEqual(len(BINARY_SHA256), 64)

    def test_supported_exact_score(self):
        row = fixtures()[0]
        got = score(row, shadow("SHADOW_RESULT", "total", 42))
        self.assertTrue(got["correct"])
        self.assertFalse(got["wrong_emitted"])

    def test_supported_wrong_value_is_not_partial_credit(self):
        row = fixtures()[0]
        got = score(row, shadow("SHADOW_RESULT", "total", 41))
        self.assertFalse(got["correct"])
        self.assertTrue(got["wrong_emitted"])

    def test_supported_wrong_operation_is_wrong(self):
        row = fixtures()[0]
        got = score(row, shadow("SHADOW_RESULT", "difference_max_min", 42))
        self.assertFalse(got["correct"])
        self.assertTrue(got["wrong_emitted"])

    def test_supported_abstain_is_counted(self):
        got = score(fixtures()[0], shadow("SHADOW_ABSTAIN"))
        self.assertFalse(got["correct"])
        self.assertTrue(got["abstain_supported"])

    def test_unsupported_abstain_and_false_positive(self):
        row = fixtures()[16]
        self.assertTrue(score(row, shadow("SHADOW_ABSTAIN"))["correct"])
        self.assertTrue(score(row, shadow("SHADOW_RESULT", "total", 20))
                        ["unsupported_false_positive"])

    def test_invented_number_occurrence(self):
        self.assertEqual(invented_numbers([{"name": "A", "number": 3},
                                           {"name": "B", "number": 4}], "A 3, B 4"), 0)
        self.assertEqual(invented_numbers([{"name": "A", "number": 3},
                                           {"name": "B", "number": 3}], "A 3, B 4"), 1)

    def test_frozen_signal_threshold_and_no_promotion(self):
        rows = []
        for i, row in enumerate(fixtures()):
            sh = (shadow("SHADOW_RESULT", row["expected_operation"], row["expected_answer"])
                  if i < 16 else shadow("SHADOW_ABSTAIN"))
            rows.append({"status": "NATIVE_ROW_COMPLETE", "score": score(row, sh),
                         "invented_nonaggregate": 0})
        result = outcome(rows, True)
        self.assertEqual(result["status"], "NATIVE_DE83_SHADOW_PILOT_SIGNAL")
        self.assertEqual(result["supported_correct"], 16)
        rows[0]["score"] = score(fixtures()[0], shadow("SHADOW_RESULT", "total", -1))
        self.assertEqual(outcome(rows, True)["status"], "NATIVE_DE83_SHADOW_PILOT_SIGNAL")
        rows[1]["score"] = score(fixtures()[1], shadow("SHADOW_RESULT", "total", -1))
        self.assertEqual(outcome(rows, True)["status"], "NATIVE_DE83_SHADOW_NOT_SUPPORTED")
        self.assertEqual(outcome(rows, False)["status"], "PILOT_PARTIAL_RED")

    def test_unsupported_false_positive_blocks_signal(self):
        rows = []
        for row in fixtures():
            sh = (shadow("SHADOW_RESULT", row["expected_operation"], row["expected_answer"])
                  if row["expected_operation"] is not None else shadow("SHADOW_ABSTAIN"))
            rows.append({"status": "NATIVE_ROW_COMPLETE", "score": score(row, sh),
                         "invented_nonaggregate": 0})
        rows[16]["score"] = score(fixtures()[16], shadow("SHADOW_RESULT", "total", 20))
        self.assertEqual(outcome(rows, True)["status"], "NATIVE_DE83_SHADOW_NOT_SUPPORTED")

    def test_no_fake_native_without_model(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "pilot"
            with self.assertRaises((ValueError, FileNotFoundError, KeyError)):
                native_capture(Path(td) / "home", out)
            self.assertFalse((out / "report.json").exists())


if __name__ == "__main__":
    unittest.main()
