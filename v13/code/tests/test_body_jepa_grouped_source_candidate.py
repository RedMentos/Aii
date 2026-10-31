"""Run117BD research-only grouped source binding, including real Torch if present."""
import unittest

from v13 import body_jepa_grouped_source_candidate as c


def row(sid, view, *, path="B1_DETAIL", weight=1.0):
    sha = {"A": "a" * 64, "B": "b" * 64, "C": "c" * 64}[sid]
    return {"path": path, "source_id": sid, "source_sha256": sha,
            "context_source_sha256": sha, "target_source_sha256": sha,
            "view_id": view, "eligibility": weight}


class GroupedSourcePreflight(unittest.TestCase):
    def setUp(self):
        self.rows = [row("A", "a1"), row("A", "a2"), row("B", "b1")]

    def test_two_source_groups_with_duplicate_views(self):
        b = c.validate_training_rows(self.rows, heldout_rows=[row("C", "c1")])
        self.assertEqual((b["source_group_count"], b["repeated_view_count"]), (2, 1))
        self.assertEqual(b["groups"], ("a" * 64, "a" * 64, "b" * 64))
        self.assertEqual(len(b["cohort_sha256"]), 64)
        self.assertEqual((b["authority"], b["native_calls"], b["runtime_jepa_weight"]), (0, 0, 0))
        self.assertFalse(b["utility_proven"])
        self.assertEqual(b, c.validate_training_rows(list(self.rows), heldout_rows=[row("C", "c1")]))

    def test_misaligned_target_ref_rejected(self):
        r = [dict(x) for x in self.rows]
        r[0]["target_source_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_TARGET_MISMATCH_RED"):
            c.validate_training_rows(r)

    def test_rebound_id_and_alias_hash_rejected(self):
        for key, value, code in (("source_sha256", "b" * 64, "SOURCE_TARGET_MISMATCH_RED"),
                                 ("source_id", "B", "SOURCE_HASH_ALIAS_RED")):
            r = [dict(x) for x in self.rows]
            r[0][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, code):
                c.validate_training_rows(r)
        r = [dict(x) for x in self.rows]
        r[2]["source_id"] = "A"
        with self.assertRaisesRegex(ValueError, "SOURCE_ID_REBOUND_RED"):
            c.validate_training_rows(r)

    def test_heldout_leak_and_duplicate_views_rejected(self):
        with self.assertRaisesRegex(ValueError, "HELDOUT_SOURCE_LEAK_RED"):
            c.validate_training_rows(self.rows, heldout_rows=[row("A", "new")])
        with self.assertRaisesRegex(ValueError, "DUPLICATE_VIEW_RED"):
            c.validate_training_rows(self.rows, heldout_rows=[row("C", "a1")])

    def test_mixed_path_and_all_same_group_refused(self):
        with self.assertRaisesRegex(ValueError, "MIXED_BODY_PATH_RED"):
            c.validate_training_rows(self.rows, heldout_rows=[row("C", "c1", path="B2_GIST")])
        with self.assertRaisesRegex(ValueError, "NO_GENUINE_NEGATIVE_RED"):
            c.validate_training_rows([row("A", "a1"), row("A", "a2")])

    def test_invalid_eligibility_refused(self):
        for value in (True, -0.1, 1.1, float("nan"), float("inf"), "1"):
            r = [dict(x) for x in self.rows]
            r[0]["eligibility"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "ELIGIBILITY_RED"):
                c.validate_training_rows(r)
        r = [dict(x, eligibility=0) for x in self.rows]
        with self.assertRaisesRegex(ValueError, "ZERO_ELIGIBILITY_RED"):
            c.validate_training_rows(r)

    def test_malformed_rows_and_bounds_refused(self):
        for rows in ([], [self.rows[0]], self.rows * 22, [None, self.rows[1]],
                     [dict(self.rows[0], view_id=" a "), self.rows[1]],
                     [dict(self.rows[0], source_sha256="x" * 64), self.rows[1]]):
            with self.subTest(rows=str(rows)[:25]), self.assertRaises(ValueError):
                c.validate_training_rows(rows)

    def test_loss_forwards_exact_source_groups_without_torch_dependency(self):
        from unittest.mock import patch
        from v13 import body_jepa_contrastive_shadow
        with patch.object(body_jepa_contrastive_shadow, "loss_and_metrics",
                          return_value=("synthetic_loss", {"masked_false_negatives": 2})) as call:
            loss, metrics = c.research_loss(None, object(), object(), self.rows,
                                            heldout_rows=[row("C", "c1")])
        self.assertEqual(loss, "synthetic_loss")
        self.assertEqual(call.call_args.kwargs["groups"],
                         ("a" * 64, "a" * 64, "b" * 64))
        self.assertEqual(call.call_args.kwargs["weights"], (1.0, 1.0, 1.0))
        self.assertEqual(metrics["source_group_count"], 2)
        self.assertEqual(metrics["masked_false_negatives"], 2)
        self.assertNotIn("groups", metrics)

    def test_source_hash_not_disclosed_in_loss_metrics(self):
        try:
            import torch
        except ImportError:
            self.skipTest("Torch not installed; metadata preflight still tested")
        target = torch.tensor([[1., 0., 0.], [1., 0., 0.], [0., 1., 0.]],
                              requires_grad=True)
        student = (target.detach() + 0.05 * torch.tensor([[0., 1., 0.],
                                                         [0., -1., 0.],
                                                         [1., 0., 0.]])).requires_grad_()
        from v13.body_jepa_contrastive_shadow import loss_and_metrics
        unmasked, _ = loss_and_metrics(torch, student, target)
        masked, metrics = c.research_loss(torch, student, target, self.rows)
        self.assertLess(float(masked.detach()) + 0.1, float(unmasked.detach()))
        self.assertEqual(metrics["masked_false_negatives"], 2)
        self.assertNotIn("source_id", metrics)
        self.assertNotIn("groups", metrics)
        self.assertEqual(metrics["source_authentication"], "REQUIRED_EXTERNAL")
        masked.backward()
        self.assertIsNone(target.grad)
        self.assertGreater(float(student.grad.abs().sum()), 0.)
        self.assertFalse(metrics["body_jepa_available"])


if __name__ == "__main__":
    unittest.main()
