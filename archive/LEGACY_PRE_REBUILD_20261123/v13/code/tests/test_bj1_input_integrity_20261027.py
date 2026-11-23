"""Independent WP-BJ1 negative controls: reject invalid shadow JEPA inputs before optimizer update."""
import math
import unittest
from v13 import body_jepa as bj

try:
    import torch
except ImportError:
    torch = None


class Tiny(torch.nn.Module if torch else object):
    def __init__(self):
        super().__init__()
        self.emb = torch.nn.Embedding(16, 8)
        self.lin = torch.nn.Linear(8, 8)

    def forward(self, input_ids, attention_mask=None, output_hidden_states=False):
        x = self.lin(self.emb(input_ids))
        return type("Out", (), {"hidden_states": (x,)})()


@unittest.skipIf(torch is None, "torch missing (CI must install, not count skips as proof)")
class BJ1InputIntegrity(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(19)
        self.model = Tiny()
        self.pred = bj.make_predictor(torch, 8)
        self.ctx = bj.pad(torch, [[1, 2, 3], [4, 5], [6, 7, 8]])
        self.tgt = bj.pad(torch, [[2, 3], [4, 5], [6, 7]])
        self.base = torch.randn(3, 8)

    def loss(self, **kw):
        return bj.jepa_loss(torch, self.model, self.pred, self.ctx, self.tgt,
                            kw.pop("mode", "base"), base_targets=self.base, **kw)[0]

    def test_nonfinite_and_mismatched_eligibility_fail_closed(self):
        for bad in ([float("nan"), 1, 1], [float("inf"), 1, 1],
                    [float("-inf"), 1, 1], [-1, 1, 1], [0, 0, 0],
                    [1, 1], [[1], [1], [1]]):
            with self.subTest(weights=repr(bad)), self.assertRaises(ValueError):
                self.loss(weights=bad)
        self.assertTrue(math.isfinite(float(self.loss(weights=[.5, 1, .25]))))

    def test_shuffled_target_requires_true_derangement(self):
        for bad in ([0, 0, 0], [0, 2, 1], [1, 1, 0], [-1, 0, 1], [1, 2],
                    [True, 2, 0]):
            with self.subTest(perm=bad), self.assertRaises(ValueError):
                self.loss(mode="shuffled", perm=bad)
        self.assertTrue(math.isfinite(float(self.loss(mode="shuffled", perm=[1, 2, 0]))))

    def test_zero_length_and_empty_context_refused(self):
        for bad in ([], [[1, 2], []], [[]]):
            with self.subTest(seqs=bad), self.assertRaises(ValueError):
                bj.pad(torch, bad)
        with self.assertRaises(ValueError):
            bj.last_token_latent(torch, self.model,
                                 (torch.tensor([[1, 2], [3, 0]]), torch.tensor([2, 0])))
        self.assertEqual(bj.pad(torch, [[1], [2, 3]])[0].shape, (2, 2))

    def test_minor_subspace_rejects_zero_nonfinite_and_bad_rank(self):
        class Wrapped:
            def __init__(self, weight):
                self.base_layer = torch.nn.Linear(4, 4, bias=False)
                with torch.no_grad():
                    self.base_layer.weight.copy_(weight)
                self.lora_A = {"default": torch.nn.Linear(4, 2, bias=False)}
                self.lora_B = {"default": torch.nn.Linear(2, 4, bias=False)}
        class Fake:
            def __init__(self, weight):
                self.w = Wrapped(weight)
            def named_modules(self):
                return [("wrapped", self.w)]
        for w in (torch.zeros(4, 4), torch.full((4, 4), float("nan"))):
            with self.assertRaises(ValueError):
                bj.minor_subspace_init(torch, Fake(w), 2)
        with self.assertRaises(ValueError):
            bj.minor_subspace_init(torch, Fake(torch.eye(4)), 5)
        good = bj.minor_subspace_init(torch, Fake(torch.eye(4)), 2)
        self.assertEqual(good["modules"], 1)
        self.assertTrue(math.isfinite(good["mean_low_singular_mass_share"]))


if __name__ == "__main__":
    unittest.main()
