"""Run581 strict score and immutable source boundary negative tests."""
import json
from pathlib import Path
import tempfile
import unittest
from scripts import run581_partial_postflight as R

ORACLE = {"project": "Fixture", "action": "A",
          "options": [{"entity": "A", "cost": 4, "remaining": 3,
                       "days": 2, "local": True, "eligible": True}]}
ANSWER = {"project": "Fixture", "action": "A", "options": ORACLE["options"]}


class PartialPostflight(unittest.TestCase):
    def test_strict_oracle_full_score(self):
        self.assertEqual(R.rescore(json.dumps(ANSWER), ORACLE), 1.)

    def test_wrong_committed_not_exact(self):
        changed = dict(ANSWER, action="B")
        self.assertEqual(R.rescore(json.dumps(changed), ORACLE), 6 / 7)

    def test_malformed_or_missing_fields_score_zero(self):
        self.assertEqual(R.rescore("not-json", ORACLE), 0.)
        self.assertEqual(R.rescore(json.dumps(dict(ANSWER, extra=True)), ORACLE), 0.)
        self.assertEqual(R.rescore(json.dumps(dict(ANSWER, options=[])), ORACLE), 0.)

    def test_bool_vs_int_is_not_equal_in_strict_score(self):
        changed = dict(ANSWER, options=[dict(ORACLE["options"][0], cost=True)])
        self.assertEqual(R.rescore(json.dumps(changed), ORACLE), 6 / 7)

    def test_missing_safe_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "SAFE_ARCHIVE_MISSING"):
                R.audit(Path(tmp) / "absent.zip")

    def test_wrong_outer_sha_refuses_even_valid_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fake.zip"
            path.write_bytes(b"not a safe original")
            with self.assertRaisesRegex(ValueError, "SAFE_OUTER_SHA_CHANGED"):
                R.audit(path)

    def test_fixed_partial_scope(self):
        self.assertEqual(R.MISSING_STAGE, "A_s33_p02")
        self.assertEqual(len(R.STAGES), 2)
        self.assertEqual(set(s for s, _ in R.STAGES), {"A_s33_p03", "A_s33_p04"})
        self.assertEqual(len(R.VARIANTS), 7)


if __name__ == "__main__":
    unittest.main()
