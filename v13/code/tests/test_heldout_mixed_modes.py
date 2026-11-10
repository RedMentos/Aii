"""Regression: heldout probe must preserve mixed child training modes."""
import contextlib
import unittest

try:
    import torch
except ImportError:
    torch = None

from v13.body_jepa import heldout_retention_kl


@unittest.skipIf(torch is None, "torch unavailable")
class HeldoutMixedModeTests(unittest.TestCase):
    def make_model(self):
        class Tiny(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.emb = torch.nn.Embedding(8, 5)
                self.dropout = torch.nn.Dropout(0.7)
                self.base = torch.nn.Linear(5, 8, bias=False)
                self.adapter = torch.nn.Linear(5, 8, bias=False)
                self.adapter_enabled = True
                self.base.requires_grad_(False)
                with torch.no_grad():
                    self.adapter.weight.zero_()

            @contextlib.contextmanager
            def disable_adapter(self):
                prev = self.adapter_enabled
                self.adapter_enabled = False
                try:
                    yield
                finally:
                    self.adapter_enabled = prev

            def forward(self, input_ids):
                x = self.dropout(self.emb(input_ids))
                y = self.base(x)
                if self.adapter_enabled:
                    y = y + self.adapter(x)
                return type("Output", (), {"logits": y})()

        model = Tiny()
        model.train()
        model.emb.eval()
        model.dropout.eval()
        return model

    def flags(self, model):
        return [m.training for m in model.modules()]

    def test_success_preserves_mixed_modes(self):
        model = self.make_model()
        original = self.flags(model)
        self.assertEqual(len(heldout_retention_kl(torch, model, [[1, 2, 3]])), 1)
        self.assertEqual(self.flags(model), original)
        self.assertTrue(model.adapter_enabled)

    def test_forward_error_preserves_mixed_modes(self):
        model = self.make_model()
        original = self.flags(model)
        with self.assertRaises(IndexError):
            heldout_retention_kl(torch, model, [[99]])
        self.assertEqual(self.flags(model), original)
        self.assertTrue(model.adapter_enabled)

    def test_invalid_second_probe_preserves_mixed_modes(self):
        model = self.make_model()
        original = self.flags(model)
        with self.assertRaises(ValueError):
            heldout_retention_kl(torch, model, [[1], []])
        self.assertEqual(self.flags(model), original)
        self.assertTrue(model.adapter_enabled)

    def test_repeatability_with_mixed_dropout(self):
        model = self.make_model()
        with torch.no_grad():
            model.adapter.weight.normal_(0, 0.15)
        values = [heldout_retention_kl(torch, model, [[1, 2, 3]])[0] for _ in range(3)]
        self.assertTrue(all(abs(x-values[0]) < 1e-7 for x in values), values)


if __name__ == "__main__":
    unittest.main()
