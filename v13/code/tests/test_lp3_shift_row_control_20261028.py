"""LP3 shifted assignment must be wrong-source for *every* row.

Tiny synthetic GPT2 only. This is a control-validity regression, not model
utility, native LFM2 or a production C3/JEPA learning claim.
"""
import unittest
import torch
from transformers import GPT2Config, GPT2LMHeadModel
from v13.lp3_state_prefix import StateConditionedPrefix


class LP3ShiftRowControl(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(73)
        base = GPT2LMHeadModel(GPT2Config(
            vocab_size=32, n_positions=48, n_ctx=48, n_embd=16,
            n_layer=1, n_head=2, bos_token_id=1, eos_token_id=2))
        self.candidate = StateConditionedPrefix(base, prefix_tokens=2)
        self.a = [3, 4, 5]
        self.b = [6, 7, 8]
        self.c = [9, 10, 11]
        self.answers = torch.tensor([[12, 13], [14, 15], [16, 17]],
                                    dtype=torch.long)

    def assert_rejects_identity_in_shift(self, rows):
        prompt = torch.tensor(rows, dtype=torch.long)
        answer = self.answers[:len(rows)]
        for call in (
            lambda: self.candidate.answer_logits(prompt, answer, 'shift'),
            lambda: self.candidate.next_token_logits(prompt, 'shift'),
            lambda: self.candidate.greedy(prompt, max_new_tokens=2,
                                          assignment='shift'),
        ):
            with self.subTest(rows=rows, call=call.__code__.co_firstlineno):
                with self.assertRaisesRegex(ValueError, 'distinct source prompt per row'):
                    call()

    def test_adjacent_duplicate_is_not_a_wrong_source_control(self):
        # Row 1 would receive row 0's identical state after roll(1).
        self.assert_rejects_identity_in_shift([self.a, self.a, self.b])

    def test_wraparound_duplicate_is_not_a_wrong_source_control(self):
        # Row 0 would receive last row's identical state after roll(1).
        self.assert_rejects_identity_in_shift([self.a, self.b, self.a])

    def test_valid_shifted_controls_keep_existing_assignment(self):
        for rows in ([self.a, self.b], [self.a, self.b, self.c],
                     [self.a, self.b, self.c, self.b]):
            # Non-adjacent duplicates are valid if every rolled predecessor differs.
            prompt = torch.tensor(rows, dtype=torch.long)
            logits = self.candidate.next_token_logits(prompt, 'shift')
            self.assertEqual(tuple(logits.shape), (len(rows), 32))
            self.assertTrue(bool(torch.isfinite(logits).all()))


if __name__ == '__main__':
    unittest.main()
