"""Body-JEPA optional EMA target eval-mode diagnostic; tiny torch only."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from v13 import body_jepa as bj

try:
    import torch
except ImportError:
    torch = None


class DropTiny(torch.nn.Module if torch else object):
    def __init__(self):
        super().__init__()
        self.emb = torch.nn.Embedding(32, 16)
        self.drop = torch.nn.Dropout(p=0.6)
        self.lin = torch.nn.Linear(16, 16)

    def forward(self, input_ids, attention_mask=None, output_hidden_states=False):
        h = self.lin(self.drop(self.emb(input_ids)))
        return type("O", (), {"hidden_states": (h,)})()


@unittest.skipIf(torch is None, "torch unavailable")
class BodyJepaTargetEvalRun11(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(13)
        self.m = DropTiny()
        for p in self.m.emb.parameters():
            p.requires_grad_(False)
        self.ema = bj.EmaAdapter(list(self.m.lin.parameters()), 0.9)
        self.ctx = bj.pad(torch, [[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        self.tgt = bj.pad(torch, [[3, 2], [5, 4], [9, 8]])

    def target(self, eval_target):
        return bj.ema_target_latent(
            torch, self.m, self.tgt, self.ema, layer=-1,
            eval_target=eval_target)

    def test_original_train_target_is_stochastic_under_dropout(self):
        self.m.train()
        a = self.target(False)
        b = self.target(False)
        self.assertFalse(torch.equal(a, b), "original target path must be a real stochastic control")
        self.assertFalse(a.requires_grad)
        self.assertTrue(self.m.training)

    def test_opt_in_eval_target_repeats_exactly_without_student_grad_loss(self):
        self.m.train()
        a = self.target(True)
        b = self.target(True)
        self.assertTrue(torch.equal(a, b))
        self.assertFalse(a.requires_grad)
        self.assertTrue(self.m.training)
        pred = bj.make_predictor(torch, 16)
        self.m.zero_grad()
        loss, detached = bj.jepa_loss(
            torch, self.m, pred, self.ctx, self.tgt, "ema", base_targets=a)
        self.assertFalse(detached.requires_grad)
        loss.backward()
        self.assertGreater(float(self.m.lin.weight.grad.abs().sum()), 0)
        self.assertTrue(self.m.drop.training)

    def test_preserves_mixed_child_train_eval_flags(self):
        self.m.train()
        self.m.emb.eval()
        before = [(id(m), m.training) for m in self.m.modules()]
        self.target(True)
        after = [(id(m), m.training) for m in self.m.modules()]
        self.assertEqual(before, after)

    def test_forward_error_restores_ema_swap_and_all_module_flags(self):
        self.m.train()
        self.m.emb.eval()
        before = [p.detach().clone() for p in self.m.lin.parameters()]
        flags = [(id(m), m.training) for m in self.m.modules()]
        with patch.object(self.m, "forward", side_effect=RuntimeError("injected target failure")):
            with self.assertRaisesRegex(RuntimeError, "injected target failure"):
                self.target(True)
        self.assertEqual(flags, [(id(m), m.training) for m in self.m.modules()])
        for p, expected in zip(self.m.lin.parameters(), before):
            self.assertTrue(torch.equal(p, expected))

    def test_non_boolean_eval_target_is_rejected(self):
        with self.assertRaises(ValueError):
            self.target("true")


if __name__ == "__main__":
    unittest.main()
