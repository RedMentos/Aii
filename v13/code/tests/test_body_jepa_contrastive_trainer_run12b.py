"""Run12B tiny real Torch+PEFT fit contract; not native 350M utility evidence."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch
from transformers import GPT2Config, GPT2LMHeadModel

from v13 import body_jepa_contrastive_trainer_shadow as port


class TinyTokenizer:
    pad_token_id = 0

    def apply_chat_template(self, messages, add_generation_prompt=True, tokenize=False):
        assert add_generation_prompt and tokenize is False
        return "Q: " + messages[0]["content"] + " A:"

    def __call__(self, text, add_special_tokens=False):
        assert add_special_tokens is False
        return {"input_ids": [(ord(c) % 96) + 1 for c in str(text)[:90]]}

    def decode(self, ids, skip_special_tokens=True):
        return ""


class TinyTrainer(port.ContrastiveBodyJepaTrainer):
    def _load(self):
        torch.set_num_threads(1)
        torch.manual_seed(int(self.cfg["seed"]))
        model = GPT2LMHeadModel(GPT2Config(
            vocab_size=128, n_positions=128, n_ctx=128,
            n_embd=32, n_layer=1, n_head=4,
            bos_token_id=1, eos_token_id=2))
        model.eval()
        return torch, TinyTokenizer(), model

    @staticmethod
    def _greedy(torch, model, ids, n):
        return []


ITEMS = [
    {"memory_id": "synthetic_0", "prompt": "In Avelorn what is copper key?", "target": "Kestrel"},
    {"memory_id": "synthetic_1", "prompt": "In Brimora what is jade key?", "target": "Nimbus"},
    {"memory_id": "synthetic_2", "prompt": "In Caelith what is indigo key?", "target": "Saffron"},
    {"memory_id": "synthetic_3", "prompt": "In Dornwick what is ivory key?", "target": "Talon"},
]


class ContrastiveTrainerPortRun12B(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def cfg(self, *, mode="ema", weight=.25):
        return {
            "rank": 2, "alpha": 4., "lr": 5e-4,
            "weight_decay": 0., "max_steps": 2, "min_steps": 2,
            "target_loss": -1., "max_tokens": 64,
            "targets": ["c_attn"], "threads": 1,
            "anchors_per_step": 0, "anchor_weight": 0.,
            "locality_swaps": 0, "seed": 223,
            "jepa_weight": weight, "jepa_target": mode,
            "jepa_ema_decay": .9, "jepa_target_eval": True,
            "contrastive_temperature": .1,
            "checkpoint_resume": False,
        }

    def trainer(self, cfg):
        return TinyTrainer(self.work, self.work / "work", anchors=(),
                           cfg=cfg, arch="gpt2")

    def test_real_two_step_tiny_peft_contrastive_ema_no_export(self):
        tr = self.trainer(self.cfg())
        got = tr.fit(ITEMS, "SYNTHETIC_RESEARCH_ONLY")
        self.assertEqual(got["artifact"], "NO_EXPORT")
        self.assertIsNone(got["hash"])
        self.assertEqual(got["method"], "lora-torch-cpu-bjepa-contrastive-shadow")
        m = got["metrics"]
        self.assertEqual(m["steps"], 2)
        self.assertEqual(m["ema_updates"], 2)
        self.assertEqual(m["objective"], "B_JEPA_CONTRASTIVE_ALTERNATIVE_SHADOW_V1")
        self.assertEqual(m["runtime_jepa_weight"], 0)
        self.assertFalse(m["body_jepa_available"])
        self.assertFalse(m["production_activation"])
        self.assertTrue(all(x["jepa"] is not None for x in m["loss_history"]))
        self.assertGreater(m["trainable_parameter_count"], 0)
        self.assertFalse(list(self.work.rglob("*.gguf")))
        self.assertFalse(list(self.work.rglob("*.pt")))

    def test_ce_zero_weight_does_not_call_contrastive(self):
        tr = self.trainer(self.cfg(weight=0.))
        with patch.object(port, "loss_and_metrics",
                          side_effect=AssertionError("CONTRASTIVE_CALLED_IN_CE")):
            got = tr.fit(ITEMS, "SYNTHETIC_RESEARCH_ONLY")
        self.assertEqual(got["metrics"]["steps"], 2)
        self.assertTrue(all(x["jepa"] is None for x in got["metrics"]["loss_history"]))
        self.assertEqual(got["artifact"], "NO_EXPORT")

    def test_shuffled_derangement_runs_but_has_no_gate(self):
        tr = self.trainer(self.cfg(mode="shuffled"))
        got = tr.fit(ITEMS, "SYNTHETIC_RESEARCH_ONLY")
        self.assertEqual(got["metrics"]["steps"], 2)
        self.assertEqual(sorted(got["metrics"]["shuffle_perm"]), [0, 1, 2, 3])
        self.assertTrue(all(i != j for i, j in enumerate(got["metrics"]["shuffle_perm"])))
        self.assertEqual(got["metrics"]["runtime_jepa_weight"], 0)
        self.assertFalse(got["metrics"]["body_jepa_available"])


if __name__ == "__main__":
    unittest.main()
