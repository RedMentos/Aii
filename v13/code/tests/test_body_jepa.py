"""WP-BJ1 unit tests: B-JEPA objective pieces on a tiny torch model (no real body, no weights downloaded)."""
import unittest
import numpy as np
from v13 import body_jepa as bj

try:
    import torch
except ImportError:  # pragma: no cover
    torch = None


class Tiny(torch.nn.Module if torch else object):
    """Embedding + linear 'body' with the HF-style call signature used by last_token_latent."""
    def __init__(self):
        super().__init__()
        self.emb = torch.nn.Embedding(16, 8)
        self.lin = torch.nn.Linear(8, 8)  # stands in for the trainable adapter

    def forward(self, input_ids, attention_mask=None, output_hidden_states=False):
        h = self.lin(self.emb(input_ids))
        return type('O', (), {'hidden_states': (self.emb(input_ids), h)})()


@unittest.skipIf(torch is None, 'torch missing')
class BodyJepaTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(0)
        self.m = Tiny()
        for p in self.m.emb.parameters():
            p.requires_grad_(False)
        self.params = [p for p in self.m.parameters() if p.requires_grad]
        self.ctx = bj.pad(torch, [[1, 2, 3], [4, 5], [6, 7, 8, 9]])
        self.tgt = bj.pad(torch, [[2, 3], [5, 6, 7], [9]])

    def test_effective_rank_bounds(self):
        rng = np.random.default_rng(0)
        self.assertGreater(bj.effective_rank(rng.normal(size=(40, 8))), 6)
        self.assertEqual(bj.effective_rank(np.ones((10, 8))), 0.)
        self.assertEqual(bj.effective_rank(np.ones((1, 8))), 0.)
        self.assertEqual(bj.effective_rank(np.full((4, 4), np.nan)), 0.)
        self.assertLess(bj.effective_rank(np.outer(rng.normal(size=20), rng.normal(size=8))), 1.2)

    def test_derangement_has_no_fixed_point_and_native_ints(self):
        rng = np.random.default_rng(1)
        for n in (2, 3, 7):
            p = bj.derangement(n, rng)
            self.assertTrue(all(type(v) is int and v != i for i, v in enumerate(p)))
            self.assertEqual(sorted(p), list(range(n)))
        with self.assertRaises(ValueError):
            bj.derangement(1, rng)

    def test_credit_map_rejects_bad_inputs(self):
        self.assertEqual(bj.credit_map(.5, .5)['credit'], .25)
        for bad in ((float('nan'), .5), (.5, 1.5), (-1., .5)):
            with self.assertRaises(ValueError):
                bj.credit_map(*bad)
        with self.assertRaises(ValueError):
            bj.credit_map(.5, .5, path='C3')

    def test_ema_swap_restores_student_and_tracks(self):
        ema = bj.EmaAdapter(self.params, .5)
        before = [p.detach().clone() for p in self.params]
        with torch.no_grad():
            for p in self.params:
                p.add_(1.)
        ema.update()
        student = [p.detach().clone() for p in self.params]
        with ema.swap():
            for p, s in zip(self.params, ema.shadow):
                self.assertTrue(torch.equal(p, s))
        for p, s in zip(self.params, student):
            self.assertTrue(torch.equal(p, s))
        self.assertTrue(all(torch.allclose(s, b + .5) for s, b in zip(ema.shadow, before)))
        self.assertGreater(ema.delta(), 0)
        with self.assertRaises(ValueError):
            bj.EmaAdapter(self.params, 1.)

    def test_predictor_identity_start(self):
        pred = bj.make_predictor(torch, 8)
        x = torch.randn(3, 8)
        self.assertTrue(torch.allclose(pred(x), x))

    def test_loss_modes_and_grads_only_through_student(self):
        pred = bj.make_predictor(torch, 8)
        ema = bj.EmaAdapter(self.params, .9)
        tgt_ema = None
        with torch.no_grad(), ema.swap():
            tgt_ema = bj.last_token_latent(torch, self.m, self.tgt)
        for mode, perm in (('ema', None), ('shuffled', [1, 2, 0])):
            self.m.zero_grad()
            loss, t = bj.jepa_loss(torch, self.m, pred, self.ctx, self.tgt, mode, ema=ema, base_targets=tgt_ema, perm=perm)
            self.assertFalse(t.requires_grad)
            loss.backward()
            self.assertTrue(any(p.grad is not None and float(p.grad.abs().sum()) > 0 for p in self.params))
            self.assertTrue(0 <= float(loss) <= 2)
        with self.assertRaises(ValueError):
            bj.jepa_loss(torch, self.m, pred, self.ctx, self.tgt, 'base')
        with self.assertRaises(ValueError):
            bj.jepa_loss(torch, self.m, pred, self.ctx, self.tgt, 'shuffled', ema=ema, base_targets=tgt_ema)
        with self.assertRaises(ValueError):
            bj.jepa_loss(torch, self.m, pred, self.ctx, self.tgt, 'nope')

    def test_swap_after_graph_is_the_known_failure(self):
        """Regression for the first smoke run: building the student graph, then swapping in place, breaks backward."""
        pred = bj.make_predictor(torch, 8)
        ema = bj.EmaAdapter(self.params, .9)
        out = self.m.lin(self.m.lin(self.m.emb(self.ctx[0]))).sum()  # weight needed for the input grad of layer 2
        with torch.no_grad(), ema.swap():
            pass
        with self.assertRaises(RuntimeError):
            out.backward()

    def test_zero_weights_rejected(self):
        pred = bj.make_predictor(torch, 8)
        with self.assertRaises(ValueError):
            bj.jepa_loss(torch, self.m, pred, self.ctx, self.tgt, 'base', base_targets=torch.randn(3, 8), weights=[0, 0, 0])


@unittest.skipIf(torch is None, 'torch missing')
class MinorSubspaceTests(unittest.TestCase):
    def build(self, in_d, out_d, r=2):
        from peft import LoraConfig, get_peft_model

        class M(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.w1 = torch.nn.Linear(in_d, out_d, bias=False)

            def forward(self, x):
                return self.w1(x)
        torch.manual_seed(0)
        m = get_peft_model(M(), LoraConfig(r=r, lora_alpha=4, target_modules=['w1'], lora_dropout=0., bias='none'))
        info = bj.minor_subspace_init(torch, m, r)
        return m, info

    def check(self, in_d, out_d):
        m, info = self.build(in_d, out_d)
        mod = m.base_model.model.w1
        W = mod.base_layer.weight.detach().double()
        self.assertEqual(info['modules'], 1)
        x = torch.randn(32, in_d)
        self.assertTrue(torch.allclose(m(x), x @ W.float().T, atol=1e-5))  # delta starts at exactly 0
        opt = torch.optim.SGD([p for p in m.parameters() if p.requires_grad], lr=.5)
        for _ in range(3):
            opt.zero_grad()
            (m(x) ** 2).mean().backward()
            opt.step()
        delta = (mod.lora_B['default'].weight @ mod.lora_A['default'].weight).detach().double()
        self.assertGreater(float(delta.abs().sum()), 0)
        U, S, Vh = torch.linalg.svd(W)
        top = 2
        # no component of the update along the top-2 singular directions (right side if in<=out, else left side)
        left_or_right = (delta @ Vh[:top].T) if in_d <= out_d else (U[:, :top].T @ delta)
        self.assertLess(float(left_or_right.abs().max()), 1e-5)
        self.assertFalse(mod.lora_A['default'].weight.requires_grad if in_d <= out_d else mod.lora_B['default'].weight.requires_grad)

    def test_wide_and_tall(self):
        self.check(6, 10)
        self.check(10, 6)



class WeightPreflightTests(unittest.TestCase):
    def test_invalid_weights_rejected_before_any_model_load(self):
        from unittest import mock
        trainer=object.__new__(bj.BodyJepaTrainer)
        bad=(True,'1',-1.,float('nan'),float('inf'),float('-inf'))
        for weight in bad:
            with self.subTest(weight=repr(weight)), mock.patch.object(bj.BodyJepaTrainer,'_load',side_effect=AssertionError('model load occurred')) as load:
                with self.assertRaises(ValueError):
                    trainer.fit([{'prompt':'x','target':'y','weight':weight}],base_generation=0)
                load.assert_not_called()
        for weights in ((0.,0.),(1e308,1e308)):
            with self.subTest(weights=weights), mock.patch.object(bj.BodyJepaTrainer,'_load',side_effect=AssertionError('model load occurred')) as load:
                with self.assertRaises(ValueError):
                    trainer.fit([{'prompt':'x','target':'y','weight':v} for v in weights],base_generation=0)
                load.assert_not_called()

    def test_valid_weights_preserve_baseline_and_jepa_numeric_values(self):
        items=[{'prompt':'a','target':'b'},
               {'prompt':'c','target':'d','weight':0.},
               {'prompt':'e','target':'f','weight':2.5}]
        self.assertEqual(bj.BodyJepaTrainer._validated_weights(items),[1.,0.,2.5])

if __name__ == '__main__':
    unittest.main()
