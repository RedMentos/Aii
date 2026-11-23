"""Structural and gradient tests for the M1 shared-weight JEPA base."""
from __future__ import annotations

import unittest
import numpy as np
import torch

from v14.m1.array_data import InputBundle
from v14.m1.base import (
    BaseConfig,
    DirectMAE,
    FrozenRepresentationProbe,
    M1JEPA,
    SharedWeightPredictor,
    UnsharedWeightPredictor,
    predictor_parameter_count,
    predictor_macs_per_example,
    matched_predictor_width_estimates,
    m1b_predictor_control_configs,
    predictor_budget_report,
    variance_covariance_regularizer,
)


def bundle(batch=4, length=12, horizon=3, channels=2, lags=2):
    return InputBundle(
        x=np.random.default_rng(1).normal(size=(batch, length, channels)).astype(np.float32),
        seasonal=np.random.default_rng(2).normal(size=(batch, horizon, lags, channels)).astype(np.float32),
        calendar=np.random.default_rng(3).normal(size=(batch, horizon, 4)).astype(np.float32),
    )


class BaseArchitectureTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(7)
        self.cfg = BaseConfig(channels=2, horizon=3, latent_dim=16, hidden_dim=32)

    def test_jepa_shapes_target_is_ema_and_predictor_has_gradient(self):
        model = M1JEPA(self.cfg)
        output = model(bundle(), torch.randn(4, 3, 2))
        self.assertEqual(tuple(output["context"].shape), (4, 16))
        self.assertEqual(tuple(output["prediction"].shape), (4, 16))
        self.assertEqual(tuple(output["target"].shape), (4, 16))
        self.assertFalse(output["target"].requires_grad)
        loss = model.latent_prediction_loss(output)
        loss.backward()
        self.assertTrue(any(p.grad is not None for p in model.predictor.parameters()))
        self.assertTrue(any(p.grad is not None for p in model.context_encoder.parameters()))
        self.assertTrue(all(p.grad is None for p in model.target_encoder.parameters()))

    def test_ema_updates_every_target_parameter(self):
        model = M1JEPA(self.cfg)
        with torch.no_grad():
            for p in model.context_encoder.parameters():
                p.add_(1.0)
        before = [p.clone() for p in model.target_encoder.parameters()]
        model.update_target_encoder(decay=0.5)
        for old, target, online in zip(
            before, model.target_encoder.parameters(), model.context_encoder.parameters(), strict=True
        ):
            torch.testing.assert_close(target, old * 0.5 + online * 0.5)

    def test_t1_predictor_is_exactly_g_after_f(self):
        predictor = SharedWeightPredictor(16, 32, 1)
        z = torch.randn(5, 16)
        torch.testing.assert_close(predictor(z), predictor.G(predictor.F(z)))

    def test_shared_recurrence_reuses_one_f_parameter_set_and_backprops(self):
        predictor = SharedWeightPredictor(16, 32, 4)
        z = torch.randn(5, 16, requires_grad=True)
        predictor(z).square().mean().backward()
        self.assertEqual(predictor.steps, 4)
        self.assertTrue(all(p.grad is not None for p in predictor.F.parameters()))
        self.assertEqual(len(list(predictor.F.parameters())), 8)

    def test_unshared_depth_control_has_independent_blocks(self):
        shared = SharedWeightPredictor(16, 32, 4)
        unshared = UnsharedWeightPredictor(16, 32, 4)
        self.assertGreater(predictor_parameter_count(unshared), predictor_parameter_count(shared))
        self.assertEqual(len(unshared.blocks), 4)
        self.assertNotEqual(
            id(next(unshared.blocks[0].parameters())),
            id(next(unshared.blocks[1].parameters())),
        )
        z = torch.randn(5, 16)
        self.assertEqual(tuple(unshared(z).shape), (5, 16))
        self.assertEqual(
            predictor_macs_per_example(16, 32, 4),
            predictor_macs_per_example(16, 32, 4),
        )
        widths = matched_predictor_width_estimates(256, 4)
        self.assertEqual(widths["compute_matched_wide_t1"], 512)
        self.assertEqual(widths["parameter_matched_unshared"], 128)

    def test_m1b_control_configs_measure_parameter_and_compute_matching(self):
        cfg = BaseConfig(
            channels=2, horizon=3, latent_dim=16, hidden_dim=32,
            predictor_steps=4,
        )
        controls = m1b_predictor_control_configs(cfg)
        self.assertEqual(set(controls), {
            "shared_recurrent", "unshared_compute_matched",
            "unshared_parameter_matched", "wide_t1_compute_matched",
        })
        report = predictor_budget_report(cfg)
        shared = report["shared_recurrent"]
        unshared_compute = report["unshared_compute_matched"]
        unshared_params = report["unshared_parameter_matched"]
        wide = report["wide_t1_compute_matched"]
        self.assertEqual(
            shared["linear_macs_per_example"],
            unshared_compute["linear_macs_per_example"],
        )
        self.assertLess(
            abs(unshared_params["trainable_parameters"] - shared["trainable_parameters"]),
            shared["trainable_parameters"] * 0.06,
        )
        self.assertLess(
            abs(wide["linear_macs_per_example"] - shared["linear_macs_per_example"]),
            shared["linear_macs_per_example"] * 0.02,
        )

    def test_jepa_and_direct_control_accept_unshared_predictor(self):
        cfg = BaseConfig(
            channels=2, horizon=3, latent_dim=16, hidden_dim=32,
            predictor_steps=4, predictor_kind="unshared",
        )
        jepa = M1JEPA(cfg)
        direct = DirectMAE(cfg)
        self.assertIsInstance(jepa.predictor, UnsharedWeightPredictor)
        self.assertIsInstance(direct.predictor, UnsharedWeightPredictor)
        self.assertEqual(tuple(jepa(bundle(), torch.randn(4, 3, 2))["prediction"].shape), (4, 16))
        self.assertEqual(tuple(direct(bundle()).shape), (4, 3, 2))

    def test_direct_mae_and_frozen_probe_output_shape(self):
        model = M1JEPA(self.cfg)
        direct = DirectMAE(self.cfg)
        probe = FrozenRepresentationProbe(model.context_encoder, self.cfg)
        y_direct = direct(bundle())
        y_probe = probe(bundle())
        self.assertEqual(tuple(y_direct.shape), (4, 3, 2))
        self.assertEqual(tuple(y_probe.shape), (4, 3, 2))
        self.assertTrue(all(p.grad is None for p in probe.encoder.parameters()))

    def test_variance_covariance_regularizer_is_finite(self):
        z = torch.randn(16, 32, requires_grad=True)
        loss = variance_covariance_regularizer(z)
        self.assertTrue(torch.isfinite(loss))
        loss.backward()
        self.assertIsNotNone(z.grad)

    def test_invalid_model_config_is_rejected(self):
        with self.assertRaises(ValueError):
            BaseConfig(channels=2, horizon=3, predictor_steps=3)


if __name__ == "__main__":
    unittest.main()
