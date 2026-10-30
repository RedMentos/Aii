"""Post-hoc C2 archived native/scaffold threshold evaluator (synthetic software)."""
import tempfile
from pathlib import Path
import unittest

from scripts import c2_route96_hybrid_archived_20261030 as h


def rows(native_correct=False):
    n, s = [], []
    for c in h.ROUTES:
        wrong = h.ROUTES[(h.ROUTES.index(c) + 1) % 4]
        for i in range(4):
            rid = f"{c}-{i}"
            n.append({"id": rid, "label": c,
                      "pred": c if native_correct else wrong,
                      "confidence": 1.0, "validated": True})
            s.append({"id": rid, "label": c,
                      "pred": wrong if native_correct else c})
    return n, s


class C2ArchivedHybridTests(unittest.TestCase):
    def test_scaffold_fallback_when_native_worse(self):
        n, s = rows(False)
        x = h.cross_validate(n, s)
        self.assertEqual(x["status"], "NO_C2_HYBRID_GAIN")
        self.assertEqual(x["cross_validated_hybrid"]["accuracy"], 1.)
        self.assertEqual(x["native_selected_total"], 0)
        self.assertEqual([r["threshold"] for r in x["folds"]], [1.01] * 4)
        self.assertEqual(x["paired_accuracy_delta_vs_scaffold"], 0.)
        self.assertFalse(x["c2_quality_promoted"])

    def test_train_only_threshold_can_select_native_when_it_is_better(self):
        n, s = rows(True)
        x = h.cross_validate(n, s)
        self.assertEqual(x["status"], "EXPLORATORY_HYBRID_SIGNAL_NO_PROMOTION")
        self.assertEqual(x["cross_validated_hybrid"]["accuracy"], 1.)
        self.assertEqual(x["native_selected_total"], 16)
        self.assertTrue(all(r["threshold"] <= 1 for r in x["folds"]))
        self.assertFalse(x["c2_quality_promoted"])

    def test_paired_sources_and_invalid_confidence_rejected(self):
        n, s = rows()
        h.validate(n, s)
        s[0]["id"] = "wrong"
        with self.assertRaises(ValueError):
            h.validate(n, s)
        n, s = rows()
        n[0]["confidence"] = float("nan")
        with self.assertRaises(ValueError):
            h.validate(n, s)
        n, s = rows()
        n[0]["id"] = n[1]["id"]
        with self.assertRaises(ValueError):
            h.validate(n, s)
        n, s = rows()
        n[0]["pred"] = "invented"
        with self.assertRaises(ValueError):
            h.validate(n, s)

    def test_missing_archive_cannot_be_treated_as_empty_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.zip"
            p.write_bytes(b"not the pinned archive")
            with self.assertRaisesRegex(ValueError, "ZIP SHA256"):
                h.load_archive(p)

    def test_four_fold_balance_and_macro_f1(self):
        n, s = rows()
        f = h.fold_ids(n)
        self.assertEqual([f.count(i) for i in range(4)], [4, 4, 4, 4])
        self.assertEqual(h.score([x["label"] for x in n],
                                 [x["pred"] for x in s])["macro_f1"], 1.)
        self.assertEqual(h.THRESHOLDS[-1], 1.01)


if __name__ == "__main__":
    unittest.main()
