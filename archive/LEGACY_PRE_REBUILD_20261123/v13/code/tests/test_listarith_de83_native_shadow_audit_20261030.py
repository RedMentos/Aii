"""Software-only independent scorer checks for prereg seed83; no native run."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.listarith_de83_native_shadow import fixtures, invented_numbers, score
from scripts.listarith_de83_native_shadow_audit import (
    independent_score, replay, source_invented, FIXTURE_BLOB, FIXTURE,
)
from v13.agi.listarith_de_shadow_pipeline import evaluate


class Seed83IndependentAuditTests(unittest.TestCase):
    def test_frozen_fixture_and_independent_scoring_equivalence(self):
        rows = fixtures()
        self.assertEqual(len(rows), 24)
        from scripts.listarith_de83_native_shadow import blob_sha
        self.assertEqual(blob_sha(FIXTURE), FIXTURE_BLOB)
        for row in rows:
            with self.subTest(id=row["id"]):
                raw = json.dumps({"values": row["values"]}, ensure_ascii=False)
                result = evaluate(row["text"], raw)
                self.assertEqual(independent_score(row, result), score(row, result))
                self.assertEqual(source_invented(row["values"], row["text"]),
                                 invented_numbers(row["values"], row["text"]))

    def test_unsupported_emission_is_a_false_positive(self):
        row = fixtures()[16]
        emitted = {"status": "SHADOW_RESULT", "operation": "total", "value": 20}
        s = independent_score(row, emitted)
        self.assertTrue(s["unsupported_false_positive"])
        self.assertFalse(s["correct"])

    def test_wrong_operation_and_value_rejected(self):
        row = fixtures()[12]
        s = independent_score(row, {"status": "SHADOW_RESULT",
                                    "operation": "total", "value": row["expected_answer"]})
        self.assertTrue(s["wrong_emitted"])
        self.assertFalse(s["correct"])

    def test_replay_cannot_invent_missing_native_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                replay(Path(td))


if __name__ == "__main__":
    unittest.main()
