import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import bp1_qad_nearmiss_retention as M


class NearMissRetentionTests(unittest.TestCase):
    def test_exact_frozen_counts(self):
        near, retention = M.build_rows()
        self.assertEqual((len(near), len(retention)), (16, 8))
        self.assertEqual(len({r["row_id"] for r in near}), 8)
        self.assertEqual({r["arm"] for r in near}, {"no_offer", "offer"})

    def test_source_disjoint_and_source_sha(self):
        near, _ = M.build_rows()
        self.assertFalse({r["source_project"] for r in near} & (M.TRAIN_PROJECTS | M.HELDOUT_PROJECTS))
        for row in near:
            source = row["prompt"].split(M.SOURCE_MARKER, 1)[1].split(M.ENDS[row["arm"]], 1)[0]
            self.assertEqual(M.sha(source.encode()), row["source_sha256"])
            self.assertIn(row["answer_keys"][0], source)
            self.assertNotIn(row["false_b2_hint"].casefold(), source.casefold())

    def test_no_offer_has_no_false_hint(self):
        near, _ = M.build_rows()
        for row in near:
            if row["arm"] == "no_offer":
                self.assertNotIn(row["false_b2_hint"], row["prompt"])
            else:
                self.assertIn(row["false_b2_hint"], row["prompt"])

    def test_target_is_scorer_side_only(self):
        near, _ = M.build_rows()
        for row in near:
            self.assertNotIn('"target"', row["prompt"])
            self.assertNotIn('"answer_keys"', row["prompt"])
            self.assertEqual(row["target"]["answer"], row["answer_keys"][0])

    def test_deterministic_bytes_and_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            a = M.write(Path(d) / "a")
            b = M.write(Path(d) / "b")
            self.assertEqual(a, b)
            for filename, key in (("near_miss.jsonl", "near_miss_sha256"),
                                  ("retention.jsonl", "retention_sha256")):
                raw = (Path(d) / "a" / filename).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), a[key])
                self.assertEqual(raw, (Path(d) / "b" / filename).read_bytes())
            self.assertEqual(a["future_native_requests_total"], 48)
            self.assertFalse(a["native_execution"])
            self.assertFalse(a["model_utility_proven"])
            self.assertEqual(a["gates"]["STEP2"], "UTILITY_FAIL")

    def test_existing_output_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            M.write(Path(d) / "a")
            with self.assertRaises(FileExistsError):
                M.write(Path(d) / "a")

    def test_project_overlap_rejected(self):
        altered = (("the solar roof pilot", *M.NEARMISS[0][1:]),) + M.NEARMISS[1:]
        with patch.object(M, "NEARMISS", altered):
            with self.assertRaisesRegex(ValueError, "overlap"):
                M.build_rows()

    def test_false_hint_in_source_rejected(self):
        first = M.NEARMISS[0]
        altered = ((first[0], first[1] + " April 19", *first[2:]),) + M.NEARMISS[1:]
        with patch.object(M, "NEARMISS", altered):
            with self.assertRaisesRegex(ValueError, "false hint"):
                M.build_rows()

    def test_retention_independent_from_source_cases(self):
        near, retention = M.build_rows()
        self.assertTrue(all(r["row_id"].startswith("RT-") for r in retention))
        self.assertFalse({r["row_id"] for r in near} & {r["row_id"] for r in retention})
        self.assertTrue(all(set(r) == {"row_id", "prompt", "expected", "kind"} for r in retention))


if __name__ == "__main__":
    unittest.main()
