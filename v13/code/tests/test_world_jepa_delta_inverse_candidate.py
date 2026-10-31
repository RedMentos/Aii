"""W7D delta-inverse candidate: parameter match, gradients, isolated SHADOW."""
import unittest
from unittest.mock import patch

import numpy as np

from v13 import world_jepa as base
from v13 import world_jepa_delta_inverse_candidate as delta
from v13.world_jepa_delta_balanced_candidate import (
    DeltaBalancedFullSlotWorldJEPA, AFFECTED_COPIES,
)
from tests.test_run39_world_jepa_action_balanced_fullslot import sample, FakeCore


class W7DDeltaInverseTests(unittest.TestCase):
    def test_identical_parameter_shapes_and_fixed_objective_weights(self):
        rng1 = np.random.default_rng(31)
        rng2 = np.random.default_rng(31)
        e0, p0 = base._init(rng1, 10, 6)
        e1, p1 = delta._init(rng2, 10, 6)
        self.assertEqual({k:v.shape for k,v in e0.items()},
                         {k:v.shape for k,v in e1.items()})
        self.assertEqual({k:v.shape for k,v in p0.items()},
                         {k:v.shape for k,v in p1.items()})
        i0 = base._init_inv(np.random.default_rng(1), 6)
        i1 = delta._init_inv(np.random.default_rng(1), 6)
        self.assertEqual({k:v.shape for k,v in i0.items()},
                         {k:v.shape for k,v in i1.items()})
        self.assertEqual((base.LR, base.TAU, base.VAR_W,
                          base.COV_W, base.INV_W, base.BATCH),
                         (delta.LR, delta.TAU, delta.VAR_W,
                          delta.COV_W, delta.INV_W, delta.BATCH))
        self.assertNotEqual(base.REVISION, delta.REVISION)

    def test_delta_inverse_gradient_matches_numeric_difference(self):
        rng = np.random.default_rng(8)
        enc, pred = delta._init(rng, 10, 6)
        inv = delta._init_inv(rng, 6)
        x = rng.normal(size=(8, 10))
        x2 = x + rng.normal(size=(8, 10)) * .2
        a = np.eye(6)[rng.integers(0, 6, 8)]
        zt = delta.encode(enc, x2)[0].copy()
        def extra_loss():
            on = delta.loss_grads(enc, pred, x, a, zt,
                                  inv=inv, x2=x2, inv_w=1.)
            off = delta.loss_grads(enc, pred, x, a, zt,
                                   inv=inv, x2=x2, inv_w=0.)
            return on[0] - off[0], on[3], off[3]
        _, on, off = extra_loss()
        for name, index in (("W1", (0, 0)), ("W2", (0, 0)),
                            ("b2", (0,))):
            param = enc[name]
            old = param[index]
            eps = 1e-5
            param[index] = old + eps
            plus = extra_loss()[0]
            param[index] = old - eps
            minus = extra_loss()[0]
            param[index] = old
            numerical = (plus - minus) / (2 * eps)
            analytical = (on[name] - off[name])[index]
            self.assertAlmostEqual(numerical, analytical, delta=2e-4)
        # Shared encoder bias cancels in z2-z: no static-state shortcut.
        self.assertAlmostEqual(float(np.linalg.norm(on["b2"]-off["b2"])),
                               0., delta=1e-8)

    def test_synthetic_delta_fit_no_runtime_authority(self):
        rng = np.random.default_rng(21)
        x = rng.normal(size=(64, 10))
        ids = rng.integers(0, 6, 64)
        a = np.eye(6)[ids]
        x2 = x + .05 * a[:, :1]
        model = delta.DeltaWorldJEPA(seed=21, ensemble=1)
        model.fit(x, a, x2, steps=2, log_every=1)
        self.assertEqual(model._fit_steps, 2)
        self.assertTrue(np.isfinite(model.latent(x[:2])).all())
        self.assertEqual(model.latent(x[:2]).shape, (2, 16))
        self.assertFalse(hasattr(model, "runtime_authority"))

    def test_action_balanced_rows_and_exception_atomicity(self):
        X, A, X2 = sample()
        with patch("v13.world_jepa_delta_balanced_candidate.DeltaWorldJEPA",
                   FakeCore):
            model = DeltaBalancedFullSlotWorldJEPA(seed=701).fit(
                X, A, X2, steps=9)
            xx, aa, yy, steps = model.core.rows
            self.assertEqual((xx.shape, aa.shape, yy.shape),
                             ((32, 10), (32, 6), (32, 10)))
            self.assertEqual(steps, 9)
            self.assertEqual(AFFECTED_COPIES, 4)
            old = model.core
            FakeCore.fail = True
            try:
                with self.assertRaisesRegex(RuntimeError, "synthetic-failure"):
                    model.fit(X, A, X2)
                self.assertIs(model.core, old)
            finally:
                FakeCore.fail = False


if __name__ == "__main__":
    unittest.main()
