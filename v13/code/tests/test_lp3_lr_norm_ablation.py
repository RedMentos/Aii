"""LP3 preregistered LR×frozen-prompt normalization: software-only contracts."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts import lp3_lr_norm_ablation as a
from scripts import lp3_optimizer_trajectory as trajectory
from scripts.lp3_heldout_utility import SEED, STEPS, LR, fixture, audit_fixture


class LRNormTests(unittest.TestCase):
    def test_frozen_design_and_four_distinct_arms(self):
        self.assertEqual((SEED, STEPS, LR), (109, 24, .005))
        self.assertEqual(a.ARMS, (
            ('raw', .005), ('raw', .0005),
            ('layernorm', .005), ('layernorm', .0005)))
        self.assertTrue(audit_fixture(fixture()))

    def test_explicit_native_optin_refuses_write(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'receipt.json'
            with self.assertRaisesRegex(ValueError, 'Explicit'):
                a.main(['--master', d, '--out', str(out)])
            self.assertFalse(out.exists())

    def test_normalization_is_finite_no_fitted_stats(self):
        import torch
        x = torch.tensor([[2., 4., 6., 8.], [-4., 0., 4., 8.]])
        before = x.clone()
        z = a.normalize_frozen_features(x, torch)
        self.assertEqual(z.shape, x.shape)
        self.assertTrue(torch.allclose(z.mean(-1), torch.zeros(2), atol=1e-6))
        self.assertTrue(torch.allclose(z.std(-1, unbiased=False),
                                       torch.ones(2), atol=1e-5))
        self.assertTrue(torch.equal(x, before))
        self.assertFalse(z.requires_grad)
        for bad in (torch.tensor([[1., float('nan')]]),
                    torch.tensor([[1., float('inf')]]),
                    torch.zeros((0, 4)), torch.zeros((2, 0))):
            with self.subTest(bad_shape=tuple(bad.shape)):
                with self.assertRaises(ValueError):
                    a.normalize_frozen_features(bad, torch)

    def test_normalization_keeps_predictor_parameters_identical(self):
        import torch
        from torch import nn

        class TinyBase(nn.Module):
            def __init__(self):
                super().__init__()
                self.emb = nn.Embedding(32, 8)
                self.head = nn.Linear(8, 32)
                self.config = SimpleNamespace(max_position_embeddings=128)

            def get_input_embeddings(self):
                return self.emb

            def forward(self, input_ids=None, inputs_embeds=None,
                        output_hidden_states=False, use_cache=False):
                emb = (self.emb(input_ids) if inputs_embeds is None
                       else inputs_embeds)
                states = emb.cumsum(1) / torch.arange(
                    1, emb.shape[1]+1, device=emb.device).reshape(1, -1, 1)
                return SimpleNamespace(hidden_states=(states,),
                                       logits=self.head(states))

        class TinyTokenizer:
            def apply_chat_template(self, messages, **kwargs):
                ids = torch.tensor([[1, 2, 3]], dtype=torch.long)
                return SimpleNamespace(input_ids=ids)

            def encode(self, text, add_special_tokens=False):
                return [4, 5]

        torch.manual_seed(SEED)
        torch.set_num_threads(1)
        base = TinyBase()
        raw_cls, norm_cls = a._candidate_class()
        raw = raw_cls(base, prefix_tokens=2)
        norm = norm_cls(base, prefix_tokens=2)
        norm.predictor.load_state_dict(raw.predictor.state_dict())
        norm.prefix_projector.load_state_dict(raw.prefix_projector.state_dict())
        self.assertEqual(trajectory._param_hash(raw),
                         trajectory._param_hash(norm))
        self.assertEqual(len(raw.trainable_parameters()),
                         len(norm.trainable_parameters()))
        self.assertFalse(any(p.requires_grad for p in base.parameters()))
        prompt = torch.tensor([[1, 2, 3]], dtype=torch.long)
        with torch.no_grad():
            self.assertFalse(torch.equal(raw.prompt_features(prompt),
                                         norm.prompt_features(prompt)))
        rows = fixture()
        for model, lr in ((raw, LR), (norm, a.LOW_LR)):
            receipt = a._train(model, TinyTokenizer(), torch, rows, lr)
            self.assertEqual(receipt['steps_recorded'], 24)
            self.assertEqual(len(receipt['trace']), 24)
            self.assertGreater(receipt['positive_predictor_gradient_steps'], 0)
            self.assertTrue(all(
                row['loss_finite'] and row['optimizer_moments_finite']
                for row in receipt['trace']))
        self.assertFalse(any(p.grad is not None for p in base.parameters()))

    def test_unregistered_learning_rate_rejected(self):
        import torch
        with self.assertRaises(ValueError):
            a._train(None, None, torch, fixture(), 0.001)
        with self.assertRaises(ValueError):
            a._train(None, None, torch, fixture(), True)


if __name__ == '__main__':
    unittest.main()
