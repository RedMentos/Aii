"""Run117BE opt-in grouped Body-JEPA trainer: pre-load refusals and tiny PEFT fit."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13 import body_jepa_grouped_contrastive_trainer_shadow as port
from v13.body_jepa_grouped_source_candidate import REVISION as BINDING_REVISION


def row(sid, view, prompt, target):
    sha = {"A": "a" * 64, "B": "b" * 64, "C": "c" * 64}[sid]
    return {"memory_id": "synthetic_" + view, "prompt": prompt, "target": target,
            "path": "B1_DETAIL", "source_id": sid, "source_sha256": sha,
            "context_source_sha256": sha, "target_source_sha256": sha,
            "view_id": view, "eligibility": 1.0}


ROWS = [
    row("A", "a1", "Avelorn copper key?", "Kestrel"),
    row("A", "a2", "Avelorn copper key restated?", "Kestrel"),
    row("B", "b1", "Brimora jade key?", "Nimbus"),
]
HOLDOUT = [row("C", "c1", "Caelith indigo key?", "Saffron")]


class GroupedTrainerPreflight(unittest.TestCase):
    def trainer(self, **cfg):
        return port.GroupedContrastiveBodyJepaTrainer(
            "/unused/no-model", "/unused/no-output", anchors=(), cfg=cfg)

    def test_requires_explicit_opt_in_before_any_load(self):
        with patch.object(port.GroupedContrastiveBodyJepaTrainer, "_load",
                          side_effect=AssertionError("MODEL_LOADED")):
            with self.assertRaisesRegex(ValueError, "GROUPED_SOURCE_OPT_IN_REQUIRED"):
                self.trainer().fit(ROWS, "SYNTHETIC")

    def test_rejects_shuffled_grouped_control_before_any_load(self):
        with patch.object(port.GroupedContrastiveBodyJepaTrainer, "_load",
                          side_effect=AssertionError("MODEL_LOADED")):
            with self.assertRaisesRegex(ValueError, "GROUPED_SHUFFLE_UNSUPPORTED"):
                self.trainer(grouped_source_enabled=True, jepa_target="shuffled").fit(
                    ROWS, "SYNTHETIC")

    def test_rejects_heldout_source_overlap_before_any_load(self):
        with patch.object(port.GroupedContrastiveBodyJepaTrainer, "_load",
                          side_effect=AssertionError("MODEL_LOADED")):
            with self.assertRaisesRegex(ValueError, "HELDOUT_SOURCE_LEAK_RED"):
                self.trainer(grouped_source_enabled=True,
                             heldout_source_rows=[dict(ROWS[0], view_id="a3")]).fit(
                                 ROWS, "SYNTHETIC")

    def test_rejects_wrong_target_before_any_load(self):
        forged = [dict(x) for x in ROWS]
        forged[1]["target_source_sha256"] = "b" * 64
        with patch.object(port.GroupedContrastiveBodyJepaTrainer, "_load",
                          side_effect=AssertionError("MODEL_LOADED")):
            with self.assertRaisesRegex(ValueError, "SOURCE_TARGET_MISMATCH_RED"):
                self.trainer(grouped_source_enabled=True).fit(forged, "SYNTHETIC")

    def test_no_native_or_authority_in_research_source(self):
        import inspect
        src = inspect.getsource(port.GroupedContrastiveBodyJepaTrainer)
        self.assertIn("NO_EXPORT", inspect.getsource(port.GroupedContrastiveBodyJepaTrainer._export))
        self.assertIn("groups=binding['groups']", src)
        self.assertIn("validate_training_rows", src)
        self.assertIn("runtime_jepa_weight':0", src)
        self.assertIn("production_activation':False", src)
        self.assertIn("body_jepa_available':False", src)
        self.assertEqual(BINDING_REVISION, "v13-bjepa-grouped-source-research-candidate-v1")

    def test_real_tiny_two_step_grouped_fit_when_pinned_deps_present(self):
        try:
            import torch
            from transformers import GPT2Config, GPT2LMHeadModel
            import peft  # noqa: F401
        except ImportError:
            self.skipTest("Pinned Torch/Transformers/PEFT not installed")
        class TinyTokenizer:
            pad_token_id = 0
            def apply_chat_template(self, messages, add_generation_prompt=True, tokenize=False):
                return "Q: " + messages[0]["content"] + " A:"
            def __call__(self, text, add_special_tokens=False):
                return {"input_ids": [(ord(c) % 96) + 1 for c in str(text)[:90]]}
            def decode(self, ids, skip_special_tokens=True):
                return ""
        class TinyTrainer(port.GroupedContrastiveBodyJepaTrainer):
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
        cfg = {"rank": 2, "alpha": 4., "lr": 5e-4, "weight_decay": 0.,
               "max_steps": 2, "min_steps": 2, "target_loss": -1.,
               "max_tokens": 64, "targets": ["c_attn"], "threads": 1,
               "anchors_per_step": 0, "anchor_weight": 0., "locality_swaps": 0,
               "seed": 223, "jepa_weight": .25, "jepa_target": "ema",
               "jepa_ema_decay": .9, "jepa_target_eval": True,
               "contrastive_temperature": .1, "checkpoint_resume": False,
               "grouped_source_enabled": True, "heldout_source_rows": HOLDOUT}
        with tempfile.TemporaryDirectory() as td:
            tr = TinyTrainer(td, Path(td) / "work", anchors=(), cfg=cfg, arch="gpt2")
            observed = []
            original = port.loss_and_metrics
            def spy(*args, **kwargs):
                observed.append(kwargs.get("groups"))
                return original(*args, **kwargs)
            with patch.object(port, "loss_and_metrics", side_effect=spy):
                got = tr.fit(ROWS, "SYNTHETIC_RESEARCH_ONLY")
            m = got["metrics"]
            self.assertEqual(m["steps"], 2)
            self.assertEqual(m["ema_updates"], 2)
            self.assertEqual(m["grouped_source_binding"]["source_group_count"], 2)
            self.assertEqual(m["grouped_source_binding"]["repeated_view_count"], 1)
            self.assertEqual(observed, [("a" * 64, "a" * 64, "b" * 64)] * 2)
            self.assertEqual(got["artifact"], "NO_EXPORT")
            self.assertIsNone(got["hash"])
            self.assertFalse(m["production_activation"])
            self.assertFalse(m["body_jepa_available"])
            self.assertEqual(m["runtime_jepa_weight"], 0)
            self.assertFalse(list(Path(td).rglob("*.gguf")))
            self.assertFalse(list(Path(td).rglob("*.pt")))


if __name__ == "__main__":
    unittest.main()
