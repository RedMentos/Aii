"""Regression tests for dropout-safe streamed anchor KL; no real body weights."""
import contextlib
import unittest

try:
    import torch
except ImportError:
    torch = None

from v13.body_jepa import streamed_anchor_kl


@unittest.skipIf(torch is None, "torch unavailable")
class StreamedAnchorDropoutTests(unittest.TestCase):
    def make_model(self):
        class DropoutAdapter(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.embed = torch.nn.Embedding(12, 8)
                self.dropout = torch.nn.Dropout(p=0.85)
                self.base = torch.nn.Linear(8, 12, bias=False)
                self.adapter = torch.nn.Linear(8, 12, bias=False)
                self.adapter_enabled = True
                with torch.no_grad():
                    self.adapter.weight.zero_()

            @contextlib.contextmanager
            def disable_adapter(self):
                previous = self.adapter_enabled
                self.adapter_enabled = False
                try:
                    yield
                finally:
                    self.adapter_enabled = previous

            def forward(self, input_ids):
                x = self.dropout(self.embed(input_ids))
                logits = self.base(x)
                if self.adapter_enabled:
                    logits = logits + self.adapter(x)
                return type("Output", (), {"logits": logits})()

        return DropoutAdapter()

    def test_zero_adapter_has_zero_kl_even_with_training_dropout(self):
        torch.manual_seed(7)
        model = self.make_model()
        model.train()
        values = [float(streamed_anchor_kl(torch, model, [1, 2, 3])) for _ in range(6)]
        self.assertTrue(all(abs(v) < 1e-6 for v in values), values)
        self.assertTrue(model.training)
        self.assertTrue(model.dropout.training)

    def test_adapter_gradient_and_determinism(self):
        torch.manual_seed(8)
        model = self.make_model()
        with torch.no_grad():
            model.adapter.weight.normal_(0, 0.2)
        model.train()
        values = [float(streamed_anchor_kl(torch, model, [1, 2, 3])) for _ in range(4)]
        self.assertTrue(all(abs(v - values[0]) < 1e-7 for v in values))
        loss = streamed_anchor_kl(torch, model, [1, 2, 3])
        loss.backward()
        self.assertIsNotNone(model.adapter.weight.grad)
        self.assertGreater(float(model.adapter.weight.grad.abs().sum()), 0.0)
        self.assertIsNone(model.base.weight.grad)
        self.assertTrue(model.training)

    def test_restores_mixed_child_modes_after_failure(self):
        model = self.make_model()
        model.train()
        model.dropout.eval()
        flags = [module.training for module in model.modules()]
        with self.assertRaises(ValueError):
            streamed_anchor_kl(torch, model, [99])
        self.assertEqual(flags, [module.training for module in model.modules()])
        self.assertTrue(model.adapter_enabled)

    def test_invalid_sequence_does_not_change_mode(self):
        model = self.make_model()
        model.train()
        with self.assertRaises(ValueError):
            streamed_anchor_kl(torch, model, [])
        self.assertTrue(model.training)


if __name__ == "__main__":
    unittest.main()
