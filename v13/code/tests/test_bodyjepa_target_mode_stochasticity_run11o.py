"""Run11O model-free target stochasticity probe controls and fail-closed invariants."""
import unittest

try:
    import torch
except ImportError:
    torch = None

from scripts import bodyjepa_target_mode_stochasticity_run11o as probe
from v13.body_jepa import EmaAdapter, pad


@unittest.skipIf(torch is None, "torch unavailable")
class BodyJepaTargetModeRun11O(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(137)

    def test_positive_control_detects_real_dropout(self):
        result = probe.positive_control(torch)
        self.assertGreater(result["train_repeat_max_abs"], 0)
        self.assertEqual(result["eval_repeat_max_abs"], 0)
        self.assertGreater(result["train_vs_eval_max_abs"], 0)

    def test_max_pairwise_rejects_nonfinite_and_bad_shape(self):
        x = torch.zeros(2, 3)
        self.assertEqual(probe.max_pairwise(torch, [x, x.clone()]), 0)
        for values in ([x], [x, torch.zeros(3, 2)],
                       [x, torch.full((2, 3), float("nan"))],
                       [x, torch.full((2, 3), float("inf"))]):
            with self.assertRaises(ValueError):
                probe.max_pairwise(torch, values)

    def test_no_dropout_is_true_noop_and_preserves_ema_weights(self):
        class Tiny(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.emb = torch.nn.Embedding(32, 8)
                self.lin = torch.nn.Linear(8, 8)
            def forward(self, input_ids, attention_mask=None, output_hidden_states=False):
                h = self.lin(self.emb(input_ids))
                return type("Out", (), {"hidden_states": (h,)})()
        model = Tiny()
        ema = EmaAdapter(list(model.lin.parameters()), 0.9)
        before = [p.detach().clone() for p in model.lin.parameters()]
        batch = pad(torch, [[1, 2, 3], [4, 5, 6]])
        result = probe.target_assay(torch, model, batch, ema)
        self.assertEqual(result["train_repeat_max_abs"], 0)
        self.assertEqual(result["eval_repeat_max_abs"], 0)
        self.assertEqual(result["train_vs_eval_max_abs"], 0)
        for p, old in zip(model.lin.parameters(), before):
            self.assertTrue(torch.equal(p, old))

    def test_nonzero_control_is_not_a_utility_gate(self):
        self.assertEqual(probe.SEED, 137)
        self.assertEqual(probe.TARGETS, ("Cobalt", "Vermilion"))
        self.assertEqual(probe.SOURCE_BLOB,
                         "b560d4e88fe457f381e89dfc5d6188a8ec3b306b")
        self.assertEqual(len(probe.EXPECTED_FIXTURE), 64)


if __name__ == "__main__":
    unittest.main()
