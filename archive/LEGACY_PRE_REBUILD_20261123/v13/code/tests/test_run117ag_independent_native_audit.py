"""Run117AG independent auditor stdlib adversarial unit checks."""
import json
import unittest

from scripts.run117ag_independent_native_audit import (
    _json, _oracle, _score, audit, ARMS, FIXTURE_SHA,
)
from tests.test_run117af_combined_c3_native_preflight import frozen_rows


class AuditUnit(unittest.TestCase):
    def test_all_six_independent_recipe_oracles(self):
        rows=frozen_rows()
        self.assertEqual(len(rows),6)
        for row in rows:
            with self.subTest(project=row["id"]):
                self.assertEqual(_oracle(row),row["oracle"])

    def test_strict_score_duplicate_extra_bool_nonfinite(self):
        oracle={"choice":"A","remaining":30}
        self.assertEqual(_score('{"choice":"A","remaining":30}',oracle)["correct"],1)
        for raw in (
            '{"choice":"A","choice":"B","remaining":30}',
            '{"choice":"A","remaining":30,"approved":true}',
            '{"choice":"A","remaining":true}',
            '{"choice":"A","remaining":NaN}',
            '{"choice":"B","remaining":30}',
            'not JSON',
        ):
            with self.subTest(raw=raw):
                self.assertEqual(_score(raw,oracle)["correct"],0)

    def test_json_duplicate_key_rejected(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_JSON_KEY_RED"):
            _json('{"x":1,"x":2}')

    def test_original_sha_refused_before_unzip(self):
        with self.assertRaisesRegex(ValueError,"ORIGINAL_ARTIFACT_SHA_RED"):
            audit(b"wrong",expected_sha="0"*64)

    def test_corrupt_zip_refused(self):
        with self.assertRaises(Exception):
            audit(b"not a zip",expected_sha=None)

    def test_fixed_arms_and_fixture(self):
        self.assertEqual(ARMS,("REAL_STORE_JEF_ONLY","B1B2_JEF_CONTEXTOS"))
        self.assertEqual(FIXTURE_SHA,
                         "cbaa2e2f8e92c994a63f12fdb9ff165c5082dcd8a33ef2c7c311e512749f29cf")


if __name__=="__main__":
    unittest.main()
