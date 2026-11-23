"""WP-T17 action-conditioned JEPA bench helpers: shared-encoder optimizer and the four consequence tasks (synthetic)."""
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import jepa_action_bench as jb  # noqa: E402
from v13 import predictor_worker as pw  # noqa: E402

class ActionJepa(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(3); self.k = 3; n = 60; d = 1024
        # 8-dim latent content in the 1024 tap; an action is a linear latent map near identity (the runtime predictor is
        # linear without bias): y = (z R_a) E + noise.
        E = np.linalg.qr(rng.normal(size=(d, 8)))[0].T; z = rng.normal(size=(n, 8)); X = z@E+.05*rng.normal(size=(n, d))
        R = [np.linalg.qr(np.eye(8)+.7*rng.normal(size=(8, 8)))[0] for _ in range(self.k)]
        R = [r*np.sign(np.diag(r)) for r in R]
        Y = np.stack([(z@R[j])@E+.05*rng.normal(size=(n, d)) for j in range(self.k)])
        self.X = pw.normalize(X); self.Y = np.stack([pw.normalize(Y[j]) for j in range(self.k)])

    def test_tasks_chance_for_action_blind_control(self):
        p0 = np.linalg.qr(np.random.default_rng(1).normal(size=(1024, 16)))[0]
        r = jb.tasks(lambda x, j, y: np.mean((x@p0-y@p0)**2, 1), self.X[40:], self.Y[:, 40:], self.k, np.random.default_rng(7))
        self.assertEqual(r['inverse_acc'], round(1/self.k, 4)); self.assertLess(abs(r['verify_action_auroc']-.5), .1)
        self.assertGreater(r['verify_content_auroc'], .6)

    def test_shared_encoder_learns_action_effects(self):
        tr = slice(0, 40); xtr = np.tile(self.X[tr], (self.k, 1)); ytr = self.Y[:, tr].reshape(-1, 1024); atr = np.repeat(np.arange(self.k), 40)
        p0 = np.linalg.qr(np.random.default_rng(1).normal(size=(1024, 16)))[0]
        p, q, tgt = jb.optimize_actions(xtr, ytr, atr, p0, jb.LONG | {'predictor_regularizer': 'ema', 'predictor_steps': 300}, self.k)
        self.assertEqual(len(q), self.k); self.assertEqual(p.shape, (1024, 16)); self.assertTrue(np.isfinite(p).all())
        r = jb.tasks(lambda x, j, y: np.mean(((x@p)@q[j]-y@tgt)**2, 1), self.X[40:], self.Y[:, 40:], self.k, np.random.default_rng(7))
        self.assertGreater(r['inverse_acc'], .6); self.assertGreater(r['verify_action_auroc'], .6)  # action-blind control: 1/k and .5

    def test_softmax_readout(self):
        F = np.r_[np.random.default_rng(2).normal(size=(30, 4)), np.random.default_rng(3).normal(size=(30, 4))+3]; y = np.r_[np.zeros(30, int), np.ones(30, int)]
        self.assertGreater(np.mean(jb.softmax_readout(F, y, 2)(F) == y), .95)

if __name__ == '__main__':
    unittest.main()
