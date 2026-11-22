"""WP-S3 sparse memory: TF-IDF slot selection (pure) and the memory layer on a tiny torch model when torch exists."""
import math
import tempfile
import unittest
from v13 import sparse_memory as sm

try:
    import torch
except ImportError:
    torch = None

class TfIdf(unittest.TestCase):
    def test_common_slots_lose_to_specific_ones(self):
        batch = [[1, 2, 3], [1, 2, 4], [1, 5, 4]]  # slot 1 hit 3x but also by every background doc
        background = [{1, 7}, {1, 8}, {1, 2}]
        chosen, scores = sm.tfidf_select(batch, background, 10, 3)
        self.assertNotIn(1, chosen[:2]); self.assertEqual(chosen[0], 4)  # 4: tf 2, df 0
        self.assertAlmostEqual(scores[4], 2*math.log(4/1), places=6)
        self.assertEqual(sm.tfidf_select([], background, 10, 3)[0], [])
        self.assertTrue(set(sm.tfidf_select(batch, [], 10, 10)[0]) == {1, 2, 3, 4, 5})

    def test_trainer_reports_empty_and_missing_torch(self):
        t = sm.SparseMemoryTrainer('/nonexistent', tempfile.gettempdir())
        self.assertEqual(t.fit([])['metrics']['reason'], 'EMPTY_BATCH')

@unittest.skipIf(torch is None, 'torch not installed (model-free CI)')
class Layer(unittest.TestCase):
    def tiny(self):
        nn = torch.nn
        class Block(nn.Module):
            def __init__(self): super().__init__(); self.feed_forward = nn.Linear(16, 16)
            def forward(self, x): return x+self.feed_forward(x)
        class Inner(nn.Module):
            def __init__(self): super().__init__(); self.layers = nn.ModuleList([Block() for _ in range(4)])
        class Model(nn.Module):
            def __init__(self): super().__init__(); self.model = Inner(); self.config = type('C', (), {'hidden_size': 16})()
            def forward(self, x):
                for b in self.model.layers: x = b(x)
                return x
        return Model()

    def test_zero_values_keep_base_and_masked_update_touches_only_selected_slots(self):
        torch.manual_seed(0); m = self.tiny(); x = torch.randn(2, 5, 16)
        with torch.no_grad(): base = m(x).clone()
        cfg = dict(sm.DEFAULTS, slots=64, key_dim=8, topk=4, mode='tfidf')
        mem, layer = sm.attach(torch, m, cfg); self.assertEqual(layer, 2)
        with torch.no_grad(): self.assertTrue(torch.equal(m(x), base))  # retrofit is exact until something is learned
        mem.record = []; out = m(x); hits = mem.record[0]; mem.record = None
        self.assertEqual(tuple(hits.shape), (10, 4))
        chosen = sorted(set(hits[0].tolist()))[:2]; mask = torch.zeros(64, 1); mask[chosen] = 1.
        (out**2).sum().backward(); mem.values.grad *= mask
        torch.optim.SGD([mem.values], lr=.1).step()
        changed = set((mem.values.detach().abs().sum(-1) > 0).nonzero().flatten().tolist())
        self.assertEqual(changed, set(chosen)); self.assertFalse(mem.wq.requires_grad); self.assertFalse(mem.keys.requires_grad)

    def test_keyed_slot_fires_only_inside_its_radius(self):
        torch.manual_seed(1); m = self.tiny(); x = torch.randn(1, 6, 16)
        with torch.no_grad(): base = m(x).clone()
        mem, _ = sm.attach(torch, m, dict(sm.DEFAULTS, keyed_slots=8, topk=4))
        self.assertEqual(mem.mode, 'keyed')
        with torch.no_grad(): self.assertTrue(torch.equal(m(x), base))
        mem.record_q = []; m(x); raw = mem.record_q[0]; mem.record_q = None  # FFN inputs of the memory block
        with torch.no_grad():
            mem.hkeys[0] = torch.nn.functional.normalize(raw[2], dim=-1); mem.theta[0] = .99; mem.written[0] = 1.; mem.values[0] = 5.
            out = m(x)
        diff = (out-base).abs().sum(-1)[0]
        self.assertGreater(float(diff[2]), 1.)  # the written position fires
        for i in (0, 1, 3, 4, 5): self.assertLess(float(diff[i]), 1e-3)  # random other positions sit outside the radius

if __name__ == '__main__':
    unittest.main()
