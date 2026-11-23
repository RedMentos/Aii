"""Run30 pure paired-diagnostic and fail-closed raw identity tests (synthetic)."""
from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from scripts.run30_ag12_vote_paired_raw_audit import paired_counts, open_verified


def rows(correct=()):
    c = set(correct)
    return [{"id": f"task-{i:03d}", "correct": int(i in c)} for i in range(88)]


class Run30PairedAudit(unittest.TestCase):
    def test_equal_88_rows_no_difference(self):
        x = rows(range(31))
        r = paired_counts(x, x)
        self.assertEqual(r["baseline_correct"], 31)
        self.assertEqual(r["vote_correct"], 31)
        self.assertEqual(r["both_correct"], 31)
        self.assertEqual(r["delta_correct"], 0)
        self.assertEqual(r["mcnemar_exact_two_sided_posthoc"], 1.0)

    def test_exact_discordant_counts(self):
        a = rows(list(range(17)) + [17, 18])
        b = rows(list(range(17)) + list(range(19, 33)))
        r = paired_counts(a, b)
        self.assertEqual((r["both_correct"], r["vote_only_correct"],
                          r["baseline_only_correct"], r["both_wrong"]),
                         (17, 14, 2, 55))
        self.assertEqual(r["delta_correct"], 12)
        self.assertEqual(r["mcnemar_exact_two_sided_posthoc"], 0.004181)

    def test_reordered_ids_rejected(self):
        a, b = rows(), rows()
        b[0], b[1] = b[1], b[0]
        with self.assertRaisesRegex(ValueError, "ALIGNMENT"):
            paired_counts(a, b)

    def test_duplicate_ids_rejected(self):
        a, b = rows(), rows()
        b[1]["id"] = b[0]["id"]
        a[1]["id"] = a[0]["id"]
        with self.assertRaisesRegex(ValueError, "ALIGNMENT"):
            paired_counts(a, b)

    def test_malformed_correctness_rejected(self):
        for bad in (True, "1", 2, None, -1):
            with self.subTest(bad=bad):
                a, b = rows(), rows()
                b[0]["correct"] = bad
                with self.assertRaisesRegex(ValueError, "SCHEMA"):
                    paired_counts(a, b)

    def test_partial_rows_rejected(self):
        with self.assertRaisesRegex(ValueError, "COUNT"):
            paired_counts(rows()[:-1], rows())

    def test_tampered_zip_identity_rejected_before_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "artifact.zip"
            p.write_bytes(b"not an approved original ZIP")
            with self.assertRaisesRegex(ValueError, "ZIP_SHA_MISMATCH"):
                open_verified(p, "run25")


if __name__ == "__main__":
    unittest.main()
