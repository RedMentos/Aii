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
        self.assertGreater(float((own - shifted).detach().abs().max()), 1e-8)
        self.assertTrue(bool(torch.isfinite(shifted).all()))

    def test_zero_state_control_changes_answer_logits(self):
        own = self.candidate.answer_logits(self.prompt, self.answer, 'own')
        zero = self.candidate.answer_logits(self.prompt, self.answer, 'zero')
        self.assertGreater(float((own - zero).detach().abs().max()), 1e-8)

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

    def test_target_free_next_token_inference_consumes_state(self):
        own = self.candidate.next_token_logits(self.prompt, 'own')
        shifted = self.candidate.next_token_logits(self.prompt, 'shift')
        zero = self.candidate.next_token_logits(self.prompt, 'zero')
        self.assertEqual(tuple(own.shape), (2, 32))
        self.assertGreater(float((own - shifted).detach().abs().max()), 1e-8)
        self.assertGreater(float((own - zero).detach().abs().max()), 1e-8)

    def test_greedy_is_bounded_and_uses_no_target_tokens(self):
        first = self.candidate.greedy(self.prompt, max_new_tokens=3)
        second = self.candidate.greedy(self.prompt, max_new_tokens=3)
        self.assertEqual(tuple(first.shape), (2, 3))
        self.assertTrue(torch.equal(first, second))
        self.assertTrue(bool((first >= 0).all() and (first < 32).all()))
        with self.assertRaises(ValueError):
            self.candidate.greedy(self.prompt, max_new_tokens=0)
        with self.assertRaises(ValueError):
            self.candidate.greedy(self.prompt, max_new_tokens=33)
        with self.assertRaises(ValueError):
            self.candidate.greedy(torch.ones((2, 47), dtype=torch.long), max_new_tokens=2)

    def test_variable_length_wrong_source_controls_answer_and_next_token(self):
        target = self.prompt[:1]
        answer = self.answer[:1]
        source = torch.tensor([[7, 8, 9, 10, 11]], dtype=torch.long)
        own = self.candidate.answer_logits(target, answer)
        wrong = self.candidate.answer_logits_from_source(target, source, answer)
        self.assertEqual(tuple(own.shape), tuple(wrong.shape))
        self.assertGreater(float((own - wrong).abs().max()), 1e-8)
        next_own = self.candidate.next_token_logits(target)
        next_wrong = self.candidate.next_token_logits_from_source(target, source)
        self.assertEqual(tuple(next_own.shape), tuple(next_wrong.shape))
        self.assertGreater(float((next_own - next_wrong).abs().max()), 1e-8)
        self.candidate.zero_grad(set_to_none=True)
        loss = self.candidate.answer_loss_from_source(target, source, answer)
        loss.backward()
        self.assertGreater(sum(float(p.grad.abs().sum()) for p in
                               self.candidate.predictor.parameters() if p.grad is not None), 0)
        self.assertGreater(sum(float(p.grad.abs().sum()) for p in
                               self.candidate.prefix_projector.parameters() if p.grad is not None), 0)
        self.assertTrue(all(p.grad is None for p in self.candidate.base.parameters()))
        self.assertEqual(tuple(self.candidate.greedy_from_source(
            target, source, max_new_tokens=2).shape), (1, 2))

    def test_wrong_source_rejects_identity_bad_batch_and_invalid_tokens(self):
        target = self.prompt[:1]
        answer = self.answer[:1]
        with self.assertRaises(ValueError):
            self.candidate.answer_logits_from_source(target, target, answer)
        with self.assertRaises(ValueError):
            self.candidate.answer_logits_from_source(
                target, self.prompt, answer)
        with self.assertRaises(ValueError):
            self.candidate.answer_logits_from_source(
                target, torch.tensor([[999, 2, 3]], dtype=torch.long), answer)
        with self.assertRaises(ValueError):
            self.candidate.greedy_from_source(target, target, max_new_tokens=2)
        with self.assertRaises(ValueError):
            self.candidate.next_token_logits_from_source(
                target, torch.empty((1, 0), dtype=torch.long))

    def test_supplied_features_cannot_encode_target_tokens(self):
        reference = self.candidate.prompt_features(self.prompt)
        self.assertEqual(tuple(self.candidate.answer_logits(
            self.prompt, self.answer, features=reference).shape), (2, 2, 32))
        tainted = reference.clone()
        tainted[:, 0] += self.answer[:, 0].to(tainted.dtype)
        with self.assertRaises(ValueError):
            self.candidate.answer_logits(self.prompt, self.answer, features=tainted)
        with self.assertRaises(ValueError):
            self.candidate.next_token_logits(self.prompt, features=tainted)

    def test_invalid_prompt_and_context_fail_before_base_forward(self):
        for bad in (torch.empty((0, 3), dtype=torch.long),
                    torch.tensor([[999, 2]], dtype=torch.long),
                    torch.full((1, 49), 3, dtype=torch.long)):
            with self.subTest(shape=tuple(bad.shape)):
                with self.assertRaises(ValueError):
                    self.candidate.prompt_features(bad)
        too_long = torch.full((2, 47), 3, dtype=torch.long)
        with self.assertRaises(ValueError):
            self.candidate.answer_logits(too_long, self.answer)
        with self.assertRaises(ValueError):
            self.candidate.next_token_logits(too_long)

    def test_shift_requires_distinct_prompts(self):
        duplicated = self.prompt[:1].repeat(2, 1)
        with self.assertRaises(ValueError):
            self.candidate.answer_logits(duplicated, self.answer, 'shift')

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
            self.candidate.answer_logits(self.prompt, self.answer, features=torch.ones(2, 16, dtype=torch.long))
        with self.assertRaises(ValueError):
            self.candidate.answer_logits(self.prompt, torch.tensor([[999, 10], [11, 12]]))
        with self.assertRaises(ValueError):
            StateConditionedPrefix(self.candidate.base, prefix_tokens=0)


if __name__ == '__main__':
    unittest.main()
