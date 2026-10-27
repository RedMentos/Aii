"""WP-LP3 tiny synthetic HF causal decoder controls. No real model or utility proof."""
import unittest

import torch
from transformers import GPT2Config, GPT2LMHeadModel

from v13.lp3_state_prefix import StateConditionedPrefix


class StateConditionedPrefixTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(73)
        base = GPT2LMHeadModel(GPT2Config(vocab_size=32, n_positions=48,
                                          n_ctx=48, n_embd=16, n_layer=1,
                                          n_head=2, bos_token_id=1, eos_token_id=2))
        self.candidate = StateConditionedPrefix(base, prefix_tokens=2)
        self.prompt = torch.tensor([[3, 4, 5], [6, 7, 8]], dtype=torch.long)
        self.answer = torch.tensor([[9, 10], [11, 12]], dtype=torch.long)

    def test_answer_ce_backpropagates_to_predictor_not_frozen_base(self):
        self.candidate.train()
        loss = self.candidate.answer_loss(self.prompt, self.answer)
        self.assertTrue(bool(torch.isfinite(loss)))
        loss.backward()
        self.assertTrue(any(p.grad is not None and bool((p.grad.abs() > 0).any())
                            for p in self.candidate.predictor.parameters()))
        self.assertTrue(any(p.grad is not None and bool((p.grad.abs() > 0).any())
                            for p in self.candidate.prefix_projector.parameters()))
        self.assertTrue(all(p.grad is None and not p.requires_grad
                            for p in self.candidate.base.parameters()))
        self.assertFalse(self.candidate.base.training)

    def test_answer_logits_change_when_predicted_state_is_swapped(self):
        own = self.candidate.answer_logits(self.prompt, self.answer, 'own')
        shifted = self.candidate.answer_logits(self.prompt, self.answer, 'shift')
        self.assertEqual(tuple(own.shape), (2, 2, 32))
        self.assertGreater(float((own - shifted).abs().max()), 1e-8)
        self.assertTrue(bool(torch.isfinite(shifted).all()))

    def test_zero_state_control_changes_answer_logits(self):
        own = self.candidate.answer_logits(self.prompt, self.answer, 'own')
        zero = self.candidate.answer_logits(self.prompt, self.answer, 'zero')
        self.assertGreater(float((own - zero).abs().max()), 1e-8)

    def test_training_step_does_not_modify_frozen_decoder(self):
        before = [p.detach().clone() for p in self.candidate.base.parameters()]
        opt = torch.optim.AdamW(self.candidate.trainable_parameters(), lr=.01)
        opt.zero_grad()
        self.candidate.answer_loss(self.prompt, self.answer).backward()
        opt.step()
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(before, self.candidate.base.parameters())))

    def test_prompt_state_does_not_consume_target_tokens(self):
        before = self.candidate.prompt_features(self.prompt)
        different_answer = torch.tensor([[13, 14], [15, 16]], dtype=torch.long)
        self.candidate.answer_logits(self.prompt, different_answer)
        after = self.candidate.prompt_features(self.prompt)
        self.assertTrue(torch.equal(before, after))

    def test_alignment_is_causal_t_minus_one_for_answer_tokens(self):
        features = self.candidate.prompt_features(self.prompt)
        with torch.no_grad():
            prefix = self.candidate.prefix_projector(self.candidate.predictor(features))
            prefix = prefix.reshape(2, 2, 16)
            embed = self.candidate.base.get_input_embeddings()
            seq = torch.cat((prefix, embed(self.prompt), embed(self.answer)), dim=1)
            all_logits = self.candidate.base(inputs_embeds=seq, use_cache=False).logits
            expected = all_logits[:, 4:6, :]
        actual = self.candidate.answer_logits(self.prompt, self.answer, features=features)
        self.assertTrue(torch.allclose(actual, expected, atol=1e-6))

    def test_invalid_shapes_nonfinite_and_control_fail_closed(self):
        with self.assertRaises(ValueError):
            self.candidate.answer_logits(self.prompt, self.answer.float())
        with self.assertRaises(ValueError):
            self.candidate.answer_logits(self.prompt, self.answer, 'unknown')
        with self.assertRaises(ValueError):
            self.candidate.answer_logits(self.prompt[:1], self.answer[:1], 'shift')
        with self.assertRaises(ValueError):
            self.candidate.answer_logits(self.prompt, self.answer, features=torch.full((2, 16), float('nan')))
        with self.assertRaises(ValueError):
            self.candidate.answer_logits(self.prompt, self.answer, features=torch.ones(2, 7))
        with self.assertRaises(ValueError):
            self.candidate.answer_logits(self.prompt, torch.tensor([[999, 10], [11, 12]]))
        with self.assertRaises(ValueError):
            StateConditionedPrefix(self.candidate.base, prefix_tokens=0)


if __name__ == '__main__':
    unittest.main()
