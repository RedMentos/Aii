"""IH-H25 Body-JEPA ObjectiveAdapter: actual tiny Torch gradient, zero authority."""
import unittest

import torch

from v13 import body_jepa as bj
from v13 import objectives
from v13.body_jepa_objective_bridge import AUTHORITY, research_adapter, research_loss
from tests.test_body_jepa import Tiny


class BodyJepaObjectiveBridgeTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(37)
        self.model = Tiny()
        for p in self.model.emb.parameters():
            p.requires_grad_(False)
        self.ctx = bj.pad(torch, [[1, 2, 3], [4, 5], [6, 7, 8]])
        self.tgt = bj.pad(torch, [[3, 2], [5, 4], [8, 7]])
        self.pred = bj.make_predictor(torch, 8)
        with torch.no_grad():
            target = bj.last_token_latent(torch, self.model, self.tgt)
        self.target = target.detach().clone().requires_grad_(True)
        self.batch = {
            "torch": torch, "model": self.model, "predictor": self.pred,
            "context_view_ids": self.ctx, "target_view_ids": self.tgt,
            "target_latents": self.target, "target_mode": "ema",
            "eligibility": [1., .5, .25],
            "source_ids": ["e1", "e2", "e3"],
            "target_source_ids": ["e1", "e2", "e3"],
            "path": "B1_DETAIL", "authority": AUTHORITY,
        }

    def test_unregistered_by_default_and_original_gate_unchanged(self):
        name = bj.OBJECTIVE.objective_id + "_RESEARCH_ONLY"
        self.assertNotIn(name, objectives._PLUGINS)
        a = research_adapter()
        self.assertEqual(a.status, "PARTIAL")
        self.assertEqual(a.loss_terms, ("JEPA_COSINE_ONLY",))
        self.assertIs(a.loss, research_loss)
        self.assertNotIn(name, objectives._PLUGINS)
        self.assertEqual(objectives.report({})["B_local_JEPA"]["status"], "UNAVAILABLE")
        for mode in ("RECORD_ONLY", "SHADOW", "COMMIT"):
            self.assertEqual(a.learn_gain({"learning_mode": mode, "age": 10}), 0.)

    def test_real_differentiable_loss_and_detached_target(self):
        a = research_adapter()
        loss = a.loss(self.batch)
        self.assertEqual(loss.ndim, 0)
        self.assertTrue(bool(torch.isfinite(loss.detach())))
        loss.backward()
        self.assertIsNone(self.target.grad)
        self.assertGreater(sum(float(p.grad.abs().sum()) for p in self.model.lin.parameters()), 0)
        self.assertGreater(sum(float(p.grad.abs().sum()) for p in self.pred.parameters()), 0)

    def test_true_shuffled_control_and_invalid_permutation(self):
        batch = dict(self.batch, target_mode="shuffled", perm=[1, 2, 0])
        loss = research_loss(batch)
        self.assertTrue(bool(torch.isfinite(loss.detach())))
        with self.assertRaises(ValueError):
            research_loss(dict(batch, perm=[0, 1, 2]))
        with self.assertRaises(ValueError):
            research_loss(dict(self.batch, perm=[1, 2, 0]))

    def test_source_authority_path_and_weight_fail_closed(self):
        cases = (
            {"source_ids": ["e1", "e1", "e3"]},
            {"source_ids": [{"bad": 1}, "e2", "e3"]},
            {"target_source_ids": ["e2", "e1", "e3"]},
            {"authority": "COMMIT"},
            {"path": "C3_LANGUAGE"},
            {"eligibility": [0., 0., 0.]},
            {"eligibility": [1.1, .5, .25]},
            {"eligibility": [1., float("nan"), .25]},
            {"eligibility": [1., .5]},
            {"target_mode": "unknown"},
            {"context_view_ids": (torch.tensor([1, 2]), torch.tensor([2]))},
        )
        for change in cases:
            with self.subTest(change=repr(change)):
                with self.assertRaises(ValueError):
                    research_loss(dict(self.batch, **change))

    def test_missing_inputs_never_default_to_training(self):
        for missing in ("source_ids", "target_latents", "authority", "eligibility"):
            with self.subTest(missing=missing):
                b = dict(self.batch)
                del b[missing]
                with self.assertRaisesRegex(ValueError, "Missing typed"):
                    research_loss(b)
        with self.assertRaises(ValueError):
            research_loss([])


if __name__ == "__main__":
    unittest.main()
