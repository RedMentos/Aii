"""Run12A seed223 autograd, negative controls and no-authority gates."""
from __future__ import annotations

import unittest

import torch

from v13 import body_jepa_contrastive_shadow as c


class BodyJepaContrastiveShadowRun12A(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(223)

    def test_correct_target_vs_derangement_and_detached_target(self):
        target = torch.eye(4, dtype=torch.float64, requires_grad=True)
        original = target.detach().clone()
        student = (torch.eye(4, dtype=torch.float64)
                   + 0.05 * torch.randn(4, 4, dtype=torch.float64)).requires_grad_()
        good, m = c.loss_and_metrics(torch, student, target, temperature=0.1)
        bad, bm = c.loss_and_metrics(torch, student, target, temperature=0.1,
                                    permutation=[1, 2, 3, 0])
        self.assertLess(float(good) + 0.5, float(bad))
        self.assertEqual(m["diagonal_top1"], 4)
        self.assertEqual(bm["permutation_control"], True)
        self.assertFalse(m["utility_proven"])
        self.assertFalse(m["body_jepa_available"])
        self.assertEqual((m["authority"], m["native_calls"], m["jepa_weight_runtime"]),
                         (0, 0, 0))
        good.backward()
        self.assertIsNotNone(student.grad)
        self.assertTrue(bool(torch.isfinite(student.grad).all()))
        self.assertGreater(float(student.grad.abs().sum()), 0.)
        self.assertIsNone(target.grad)
        self.assertTrue(torch.equal(target.detach(), original))

    def test_false_negative_source_group_mask_and_no_negative_refusal(self):
        target = torch.tensor([[1., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
        student = target.clone().requires_grad_()
        unmasked, _ = c.loss_and_metrics(torch, student, target)
        masked, m = c.loss_and_metrics(torch, student, target,
                                       groups=["same", "same", "other"])
        self.assertLess(float(masked) + 0.1, float(unmasked))
        self.assertEqual(m["masked_false_negatives"], 2)
        self.assertEqual(m["minimum_negatives_per_row"], 1)
        with self.assertRaisesRegex(ValueError, "NO_GENUINE_NEGATIVE_RED"):
            c.loss_and_metrics(torch, student, target,
                               groups=["same", "same", "same"])

    def test_weighted_reduction_matches_manual_cross_entropy(self):
        student = (torch.eye(4) + 0.1 * torch.randn(4, 4)).requires_grad_()
        target = torch.eye(4)
        weights = torch.tensor([1., 0., 2., 0.])
        loss, _ = c.loss_and_metrics(torch, student, target, weights=weights)
        logits = (torch.nn.functional.normalize(student, dim=-1)
                  @ target.T) / 0.1
        per = torch.nn.functional.cross_entropy(
            logits, torch.arange(4), reduction="none")
        self.assertTrue(torch.allclose(loss, (per * weights).sum() / weights.sum(),
                                       rtol=1e-6, atol=1e-6))

    def test_finite_difference_student_gradient_and_no_target_gradient(self):
        student = (torch.eye(3, dtype=torch.float64)
                   + 0.2 * torch.randn(3, 3, dtype=torch.float64)).requires_grad_()
        target = torch.eye(3, dtype=torch.float64, requires_grad=True)
        loss, _ = c.loss_and_metrics(torch, student, target, temperature=0.2)
        loss.backward()
        analytic = float(student.grad[0, 1])
        with torch.no_grad():
            plus = student.detach().clone()
            minus = student.detach().clone()
            plus[0, 1] += 1e-5
            minus[0, 1] -= 1e-5
        lp, _ = c.loss_and_metrics(torch, plus, target, temperature=0.2)
        lm, _ = c.loss_and_metrics(torch, minus, target, temperature=0.2)
        numeric = float((lp - lm) / (2e-5))
        self.assertAlmostEqual(analytic, numeric, delta=1e-4)
        self.assertIsNone(target.grad)

    def test_adversarial_shapes_values_and_permutations_fail_closed(self):
        eye = torch.eye(3)
        bad_cases = (
            (eye[:1], eye[:1], {}),
            (torch.ones(2, 1), torch.ones(2, 1), {}),
            (torch.zeros(3, 3), eye, {}),
            (eye, torch.ones(3, 3), {}),
            (eye, eye * float("nan"), {}),
            (eye, eye, {"temperature": float("inf")}),
            (eye, eye, {"temperature": True}),
            (eye, eye, {"temperature": 0.001}),
            (eye, eye, {"weights": [0., 0., 0.]}),
            (eye, eye, {"weights": [-1., 1., 1.]}),
            (eye, eye, {"weights": [float("nan"), 1., 1.]}),
            (eye, eye, {"weights": [1., 1.]}),
            (eye, eye, {"weights": [True, False, True]}),
            (eye, eye, {"groups": ["x", "y"]}),
            (eye, eye, {"groups": ["x", "x", "x"]}),
            (eye, eye, {"permutation": [0, 2, 1]}),
            (eye, eye, {"permutation": [1, 1, 0]}),
            (eye, eye, {"permutation": [1, 2]}),
            (eye, eye, {"permutation": [1, 2, 0], "groups": ["a", "b", "c"]}),
        )
        for i, (s, t, kw) in enumerate(bad_cases):
            with self.subTest(case=i):
                with self.assertRaises(ValueError):
                    c.loss_and_metrics(torch, s, t, **kw)

    def test_bounds_and_eligibility_detached(self):
        target = torch.eye(3, dtype=torch.float32)
        student = (target + 0.1 * torch.randn(3, 3)).requires_grad_()
        weights = torch.tensor([1., 2., 3.], requires_grad=True)
        loss, metrics = c.loss_and_metrics(torch, student, target, weights=weights)
        loss.backward()
        self.assertIsNone(weights.grad)
        self.assertEqual(metrics["minimum_negatives_per_row"], 2)
        self.assertFalse(metrics["whole_system_complete"])
        for bad in (torch.ones(65, 2), torch.ones(2, 4097)):
            with self.assertRaisesRegex(ValueError, "SIZE_RED"):
                c.loss_and_metrics(torch, bad, bad)


if __name__ == "__main__":
    unittest.main()
