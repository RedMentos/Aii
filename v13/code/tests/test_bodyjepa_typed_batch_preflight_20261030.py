"""RED-first IH-H25 typed research batch preflight; software-only tiny Torch."""
import unittest
import torch

from v13 import body_jepa as bj
from v13.body_jepa_objective_bridge import AUTHORITY, research_loss
from tests.test_body_jepa import Tiny


class CountingTiny(Tiny):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def forward(self, *args, **kwargs):
        self.calls += 1
        return super().forward(*args, **kwargs)


class BodyJepaTypedBatchPreflight(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(47)
        self.model = CountingTiny()
        self.ctx = bj.pad(torch, [[1, 2, 3], [4, 5], [6, 7, 8]])
        self.tgt = bj.pad(torch, [[3, 2], [5, 4], [8, 7]])
        with torch.no_grad():
            self.target = bj.last_token_latent(torch, self.model, self.tgt).detach()
        self.model.calls = 0
        self.pred = bj.make_predictor(torch, 8)
        self.batch = {
            "torch": torch, "model": self.model, "predictor": self.pred,
            "context_view_ids": self.ctx, "target_view_ids": self.tgt,
            "target_latents": self.target.clone(), "target_mode": "ema",
            "eligibility": [1., .5, .25],
            "source_ids": ["s1", "s2", "s3"],
            "target_source_ids": ["s1", "s2", "s3"],
            "path": "B1_DETAIL", "authority": AUTHORITY,
        }

    def reject_before_forward(self, **change):
        self.model.calls = 0
        with self.assertRaises(ValueError):
            research_loss(dict(self.batch, **change))
        self.assertEqual(self.model.calls, 0, "Malformed input reached model.forward")

    def test_context_and_target_view_contracts_before_forward(self):
        cases = [
            {"context_view_ids": (self.ctx[0], torch.tensor([3, 2]))},
            {"target_view_ids": (self.tgt[0], torch.tensor([2, 2]))},
            {"target_view_ids": (self.tgt[0], torch.tensor([2, 0, 2]))},
            {"target_view_ids": (self.tgt[0], torch.tensor([2, 99, 2]))},
            {"context_view_ids": (self.ctx[0].float(), self.ctx[1])},
            {"target_view_ids": (self.tgt[0].float(), self.tgt[1])},
            {"context_view_ids": (self.ctx[0], self.ctx[1].float())},
        ]
        for case in cases:
            with self.subTest(case=str(case)):
                self.reject_before_forward(**case)

    def test_target_latent_contract_before_forward(self):
        cases = [
            self.target[:2],
            self.target.unsqueeze(0),
            self.target.long(),
            torch.full_like(self.target, float("nan")),
            torch.full_like(self.target, float("inf")),
        ]
        for target in cases:
            with self.subTest(shape=tuple(target.shape), dtype=str(target.dtype)):
                self.reject_before_forward(target_latents=target)

    def test_eligibility_types_not_coerced_into_permission(self):
        for weights in (
            [True, .5, .25],
            [1., "0.5", .25],
            torch.tensor([True, False, True]),
            [[1.], [.5], [.25]],
        ):
            with self.subTest(weights=str(weights)):
                self.reject_before_forward(eligibility=weights)

    def test_shuffled_permutation_preflight(self):
        self.reject_before_forward(target_mode="shuffled", perm=[0, 2, 1])
        self.reject_before_forward(target_mode="shuffled", perm=[1, True, 0])

    def test_valid_float_tensor_eligibility_detached_from_gradient(self):
        weights = torch.tensor([1., .5, .25], requires_grad=True)
        loss = research_loss(dict(self.batch, eligibility=weights))
        self.assertEqual(loss.ndim, 0)
        self.assertTrue(bool(torch.isfinite(loss.detach())))
        self.assertEqual(self.model.calls, 1)
        loss.backward()
        self.assertIsNone(weights.grad, "Eligibility is evidence, not a trainable gate")
        self.assertGreater(sum(float(p.grad.abs().sum()) for p in self.model.lin.parameters()), 0)
        self.assertGreater(sum(float(p.grad.abs().sum()) for p in self.pred.parameters()), 0)


if __name__ == "__main__":
    unittest.main()
