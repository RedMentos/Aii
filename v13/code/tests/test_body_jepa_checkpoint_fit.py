"""Tiny synthetic HF/PEFT integration: opt-in interrupted BJ1 fit vs uninterrupted fit.
No downloaded model, no native training proof, no age promotion.
"""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import torch
from transformers import GPT2Config, GPT2LMHeadModel
from v13.body_jepa import BodyJepaTrainer
from v13.body_jepa_checkpoint import save as save_step


class Tokenizer:
    pad_token_id = 0
    def apply_chat_template(self, messages, add_generation_prompt, tokenize):
        return '<user>' + messages[0]['content'] + '<assistant>'
    def __call__(self, text, add_special_tokens=False):
        return {'input_ids': [(ord(c) % 60) + 2 for c in text]}
    def decode(self, ids, skip_special_tokens=True):
        return 'synthetic output'


class TinyTrainer(BodyJepaTrainer):
    def _load(self):
        torch.manual_seed(123)
        model = GPT2LMHeadModel(GPT2Config(vocab_size=64, n_positions=96,
                                            n_ctx=96, n_embd=16, n_layer=1, n_head=2))
        return torch, Tokenizer(), model
    @staticmethod
    def _greedy(torch_module, model, ids, n):
        return [2]
    def _export(self, torch_module, model, out, lc):
        path = out / 'adapter.gguf'
        path.write_bytes(b'SYNTHETIC_TEST_NOT_NATIVE')
        return {'gguf': str(path), 'gguf_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


class OptInFitResumeTests(unittest.TestCase):
    def test_interrupted_fit_exactly_matches_uninterrupted(self):
        cfg = {'rank': 2, 'targets': ('c_attn',), 'locality_swaps': 0,
               'anchor_weight': 0., 'jepa_weight': .3, 'jepa_target': 'ema',
               'max_steps': 2, 'min_steps': 2, 'target_loss': -1.,
               'checkpoint_resume': True, 'threads': 1, 'seed': 9}
        items = [{'memory_id': 'one', 'prompt': 'What is the item?', 'target': 'Blue'},
                 {'memory_id': 'two', 'prompt': 'Where is the item?', 'target': 'North'}]
        with tempfile.TemporaryDirectory() as root:
            base = TinyTrainer('/tmp/synthetic-master', Path(root)/'full',
                               master_sha256='a'*64, cfg=cfg)
            full = base.fit(items, 'synthetic-generation')
            self.assertEqual(full['metrics']['steps'], 2)
            self.assertEqual(full['metrics']['checkpoint_restored_step'], 0)
            broken = TinyTrainer('/tmp/synthetic-master', Path(root)/'resume',
                                 master_sha256='a'*64, cfg=cfg)
            calls = []
            def crash_after_save(*args, **kwargs):
                receipt = save_step(*args, **kwargs)
                calls.append(receipt['step'])
                raise RuntimeError('SYNTHETIC_CRASH_AFTER_FSYNC')
            with mock.patch('v13.body_jepa_checkpoint.save', side_effect=crash_after_save):
                with self.assertRaisesRegex(RuntimeError, 'SYNTHETIC_CRASH_AFTER_FSYNC'):
                    broken.fit(items, 'synthetic-generation')
            self.assertEqual(calls, [1])
            resumed = TinyTrainer('/tmp/synthetic-master', Path(root)/'resume',
                                  master_sha256='a'*64, cfg=cfg)
            result = resumed.fit(items, 'synthetic-generation')
            self.assertEqual(result['metrics']['checkpoint_restored_step'], 1)
            self.assertEqual(result['metrics']['steps'], 2)
            self.assertEqual(result['metrics']['loss_history'], full['metrics']['loss_history'])
            for (name, p), (other_name, q) in zip(base.model.named_parameters(),
                                                  resumed.model.named_parameters()):
                self.assertEqual(name, other_name)
                self.assertTrue(torch.equal(p, q), name)
            full_pred = torch.load(next((Path(root)/'full').rglob('predictor.pt')), weights_only=True)
            resumed_pred = torch.load(next((Path(root)/'resume').rglob('predictor.pt')), weights_only=True)
            for name in ('weight', 'bias'):
                self.assertTrue(torch.equal(full_pred[name], resumed_pred[name]))

if __name__ == '__main__':
    unittest.main()
