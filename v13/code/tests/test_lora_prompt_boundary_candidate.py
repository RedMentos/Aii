"""Actual frozen _encode exercised without importing torch or loading weights."""
import tempfile
import unittest
from unittest.mock import patch
from scripts import lora_prompt_boundary_candidate as candidate
from v13.common import Unavailable
from v13.lora_trainer import LoraTrainer


class TinyTokenizer:
    def apply_chat_template(self, messages, **kwargs):
        return 'user:' + messages[0]['content'] + '\nanswer:'

    def __call__(self, text, **kwargs):
        return {'input_ids': [ord(ch) for ch in text.replace('<|im_end|>', '#')]}


class PromptBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = LoraTrainer(self.temp.name, self.temp.name, cfg={'max_tokens': 16})
        self.fixed = candidate.PromptBoundLoraTrainer(self.temp.name, self.temp.name, cfg={'max_tokens': 16})
        self.tok = TinyTokenizer()

    def test_reproduces_original_all_answer_boundary_and_rejects_it(self):
        ids, labels = self.base._encode(self.tok, 'question', 'x' * 15)
        self.assertEqual(len(ids), 16)
        self.assertTrue(all(label != -100 for label in labels))
        # The original training loop's first supervised index would be zero.
        plen = next(i for i, label in enumerate(labels) if label != -100)
        self.assertEqual(plen, 0)
        self.assertEqual(ids[plen - 1], ord('#'))
        with self.assertRaisesRegex(ValueError, 'lost its prompt'):
            self.fixed._encode(self.tok, 'question', 'x' * 15)

    def test_partial_prompt_and_complete_short_pair_remain_byte_identical(self):
        for budget, target in ((16, 'ok'), (80, 'answer'), (16, 'x' * 14)):
            with self.subTest(budget=budget, target=target):
                self.base.cfg['max_tokens'] = budget
                self.fixed.cfg['max_tokens'] = budget
                self.assertEqual(self.base._encode(self.tok, 'long question', target),
                                 self.fixed._encode(self.tok, 'long question', target))

    def test_complete_pair_exactly_fits_budget(self):
        prompt, target = 'question', 'answer'
        ids, labels = self.tok(self.tok.apply_chat_template([{'content': prompt}]))['input_ids'], self.tok(target + '<|im_end|>')['input_ids']
        self.fixed.cfg['max_tokens'] = len(ids) + len(labels)
        self.assertEqual(self.fixed._encode(self.tok, prompt, target),
                         (ids + labels, [-100] * len(ids) + labels))

    def test_work_namespace_cannot_resume_original_checkpoint(self):
        self.assertNotEqual(self.base.work, self.fixed.work)
        self.assertEqual(self.fixed.work.parent.name, candidate.CANDIDATE_REVISION)
        self.assertEqual(self.fixed.work.name, self.fixed.candidate_sha256)
        self.assertNotEqual(self.fixed.method, self.base.method)

    def test_overlong_target_also_rejected_with_jepa_disabled(self):
        self.assertEqual(self.fixed.cfg['jepa_weight'], 0.)
        with self.assertRaisesRegex(ValueError, 'lost its prompt'):
            self.fixed._encode(self.tok, 'q', 'x' * 100)

    def test_invalid_budget_cannot_silently_select_full_sequence(self):
        for budget in (0, 1, -1, True, 4.0, '16', None):
            with self.subTest(budget=budget):
                self.fixed.cfg['max_tokens'] = budget
                with self.assertRaisesRegex(ValueError, 'max_tokens'):
                    self.fixed._encode(self.tok, 'question', 'answer')

    def test_prompt_only_inference_encoding_is_unchanged(self):
        self.assertEqual(self.base._encode(self.tok, 'question'), self.fixed._encode(self.tok, 'question'))

    def test_missing_target_tokens_rejected(self):
        with patch.object(LoraTrainer, '_encode', return_value=([1, 2], [-100, -100])):
            with self.assertRaisesRegex(ValueError, 'no supervised'):
                self.fixed._encode(self.tok, 'q', 'a')

    def test_unknown_original_source_is_not_silently_supported(self):
        with patch.object(candidate, 'SOURCE_SHA256', '0' * 64):
            with self.assertRaisesRegex(Unavailable, 'Unsupported source'):
                candidate.PromptBoundLoraTrainer(self.temp.name, self.temp.name)

    def test_candidate_does_not_replace_production_class(self):
        from v13 import lora_trainer
        self.assertIs(lora_trainer.LoraTrainer, LoraTrainer)
        self.assertIsNot(lora_trainer.LoraTrainer, candidate.PromptBoundLoraTrainer)


if __name__ == '__main__':
    unittest.main()
