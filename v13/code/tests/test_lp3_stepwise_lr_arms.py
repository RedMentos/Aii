"""Synthetic fixed-arm LP3 optimizer trace tests; no real model or utility proof."""
import math
from types import SimpleNamespace
import unittest

from scripts.lp3_stepwise_lr_arms import ARMS, _finite, run_arm
from scripts.lp3_heldout_utility import fixture, audit_fixture


class StepwiseLRArmTests(unittest.TestCase):
    def test_fixed_arms_and_nonfinite_recording(self):
        self.assertEqual(ARMS, (('A_original_lr', 0.005), ('B_low_lr', 0.0005)))
        self.assertEqual(_finite(0.0), 0.0)
        self.assertEqual(_finite(float('nan')), 'nan')
        self.assertEqual(_finite(float('inf')), 'inf')
        self.assertTrue(audit_fixture(fixture()))

    def test_tiny_frozen_decoder_end_to_end_stepwise_trace(self):
        import torch
        from transformers import GPT2Config, GPT2LMHeadModel

        class TinyTokenizer:
            def __init__(self):
                self.tokens = {}
            def token(self, word):
                if word not in self.tokens:
                    self.tokens[word] = len(self.tokens) + 3
                return self.tokens[word]
            def apply_chat_template(self, messages, add_generation_prompt,
                                    tokenize, return_dict, return_tensors):
                ids = [self.token(w) for w in messages[0]['content'].split()]
                return SimpleNamespace(input_ids=torch.tensor([ids], dtype=torch.long))
            def encode(self, answer, add_special_tokens=False):
                return [self.token(w) for w in answer.split()]

        torch.manual_seed(109)
        base = GPT2LMHeadModel(GPT2Config(
            vocab_size=128, n_positions=64, n_ctx=64,
            n_embd=16, n_layer=1, n_head=2))
        base.eval()
        tok = TinyTokenizer()
        rows = fixture()
        for row in rows:
            for target, source in zip(row['heldout'], row['wrong_sources']):
                self.assertNotEqual(
                    tok.apply_chat_template([{'content':target}],True,True,True,'pt').input_ids.tolist(),
                    tok.apply_chat_template([{'content':source}],True,True,True,'pt').input_ids.tolist())
        result = run_arm(base, tok, torch, rows, 'B_low_lr', 0.0005)
        self.assertEqual(result['intended_updates'], 24)
        self.assertEqual(len(result['step_trace']), 24)
        self.assertTrue(result['trainable_parameters_changed'])
        self.assertEqual(result['completed_updates'], 24)
        self.assertIsNone(result['first_bad_step'])
        self.assertTrue(all(x['gradients_finite_nonzero'] for x in result['step_trace']))
        self.assertTrue(all(math.isfinite(x['ce']) for x in result['step_trace']))
        self.assertEqual(len(result['heldout_raw_after']), 12)
        self.assertTrue(all(not p.requires_grad and p.grad is None
                            for p in base.parameters()))


if __name__ == '__main__':
    unittest.main()
