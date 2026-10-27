import unittest
import numpy as np
from v13 import world_jepa as wj


class TestWorldJEPA(unittest.TestCase):
    def test_gradients_match_finite_differences(self):
        rng = np.random.default_rng(0); d, a, n = 7, 3, 12
        old = wj.H, wj.Z, wj.HP
        wj.H, wj.Z, wj.HP = 5, 4, 6
        try:
            enc, pred = wj._init(rng, d, a)
            x = rng.normal(size=(n, d)); A = np.eye(a)[rng.integers(0, a, n)]; zt = rng.normal(size=(n, wj.Z))
            inv = wj._init_inv(rng, a); x2 = rng.normal(size=(n, d))
            f = lambda: wj.loss_grads(enc, pred, x, A, zt, 1., .5, inv=inv, x2=x2, inv_w=.7)
            _, _, gp, ge, gi = f()
            for params, grads in ((enc, ge), (pred, gp), (inv, gi)):
                for k in params:
                    i = tuple(rng.integers(0, s) for s in params[k].shape); e = 1e-6; v = params[k][i]
                    params[k][i] = v+e; lp = f()[0]
                    params[k][i] = v-e; lm = f()[0]
                    params[k][i] = v
                    self.assertAlmostEqual((lp-lm)/(2*e), grads[k][i], places=5, msg=k)
        finally:
            wj.H, wj.Z, wj.HP = old

    def _world(self, n, rng):
        # 4 slots; action k flips slot k on; noise dims are random every step and decided by no action
        X = np.concatenate([rng.integers(0, 2, (n, 4)).astype(float), rng.normal(size=(n, 4))], 1)
        act = rng.integers(0, 4, n); X2 = X.copy(); X2[np.arange(n), act] = 1-X[np.arange(n), act]; X2[:, 4:] = rng.normal(size=(n, 4))
        return X, np.eye(4)[act], X2, act

    def test_learns_action_effect_and_controls_do_not(self):
        rng = np.random.default_rng(1); X, A, X2, act = self._world(1500, rng)
        m = wj.WorldJEPA(seed=3, ensemble=3).fit(X, A, X2, steps=1500)
        c = wj.WorldJEPA(seed=3, ensemble=1).fit(X, np.zeros_like(A), X2, steps=1500)
        Xe, Ae, X2e, acte = self._world(200, np.random.default_rng(9))

        def retrieval(model, zero):
            ok = 0
            for i in range(len(Xe)):
                outs = []
                for k in range(4):
                    o = X2e[i].copy(); o[:4] = Xe[i, :4]; o[k] = 1-Xe[i, k]; outs.append(o)
                outs = np.array(outs); zt = model.latent(outs)
                p, _ = model.predict(np.repeat(Xe[i:i+1], 4, 0), np.zeros((4, 4)) if zero else np.eye(4))
                ok += sum(int(np.argmin(((zt-p[k])**2).sum(1)) == k) for k in range(4))
            return ok/(4*len(Xe))
        self.assertGreater(retrieval(m, False), .9)
        self.assertLess(retrieval(c, True), .45)
        st = m.collapse_stats(X2)
        self.assertGreater(st['min_std'], .05)

    def test_confidence_zero_coverage_is_uncertain(self):
        rng = np.random.default_rng(2); X, A, X2, _ = self._world(400, rng)
        m = wj.WorldJEPA(seed=1, ensemble=3).fit(X, A, X2, steps=300)
        conf, lab = m.confidence(X[:5], A[:5], [0, 0, 100, 100, 100])
        self.assertEqual(lab[:2], ['SIMULATION_UNCERTAIN']*2)
        self.assertTrue((conf[:2] == 0).all())


    def test_predict_uses_ensemble_mean_and_spread_from_same_members(self):
        from unittest import mock
        m=wj.WorldJEPA(seed=0,ensemble=3)
        m.preds=[0.,2.,4.]
        m.zsd=np.ones(wj.Z)
        m.latent=lambda X,target=False:np.zeros((len(X),wj.Z))
        X=np.zeros((2,3));A=np.zeros((2,4))
        def member(p,z,a):
            return np.full((len(z),wj.Z),p),None
        with mock.patch.object(wj,'predict',side_effect=member):
            mean,spread=m.predict(X,A)
            self.assertTrue(np.allclose(mean,2.))
            self.assertTrue(np.allclose(spread,np.std([0.,2.,4.])))
            m.preds=[7.]
            single,single_spread=m.predict(X,A)
            self.assertTrue(np.allclose(single,7.))
            self.assertTrue(np.allclose(single_spread,0.))


    def test_confidence_cannot_claim_coverage_for_unseen_action(self):
        m = wj.WorldJEPA(seed=0, ensemble=1)
        m._action_counts = np.array([40, 0, 0, 0])
        m.predict = lambda X, A: (np.zeros((len(X), wj.Z)), np.zeros(len(X)))
        m.ood = lambda X: np.zeros(len(X))
        X = np.zeros((1, 8)); A = np.array([[0., 1., 0., 0.]])
        conf, labels = m.confidence(X, A, [1000])
        self.assertEqual(conf.tolist(), [0.])
        self.assertEqual(labels, ['SIMULATION_UNCERTAIN'])

    def test_confidence_fails_closed_for_bad_counts_and_action_rows(self):
        m = wj.WorldJEPA(seed=0, ensemble=1)
        m._action_counts = np.array([10, 10, 10, 10])
        m.predict = lambda X, A: (np.zeros((len(X), wj.Z)), np.zeros(len(X)))
        m.ood = lambda X: np.zeros(len(X))
        X = np.zeros((5, 8))
        A = np.array([[1., 0., 0., 0.], [0., 1., 0., 0.],
                      [0., 0., 1., 0.], [1., 1., 0., 0.],
                      [0., 0., 0., 0.]])
        conf, labels = m.confidence(X, A, [float('nan'), float('inf'), -1, 100, 100])
        self.assertTrue(np.isfinite(conf).all())
        self.assertEqual(conf.tolist(), [0.] * 5)
        self.assertEqual(labels, ['SIMULATION_UNCERTAIN'] * 5)

    def test_confidence_caps_reported_counts_at_training_evidence(self):
        m = wj.WorldJEPA(seed=0, ensemble=1)
        m._action_counts = np.array([2, 0, 0, 0])
        m.predict = lambda X, A: (np.zeros((len(X), wj.Z)), np.zeros(len(X)))
        m.ood = lambda X: np.zeros(len(X))
        X = np.zeros((1, 8)); A = np.array([[1., 0., 0., 0.]])
        conf, labels = m.confidence(X, A, [1000])
        self.assertAlmostEqual(conf[0], 1 - np.exp(-2 / wj.COVER_N))
        self.assertEqual(labels, ['SIMULATION_UNCERTAIN'])

    def test_fit_rejects_malformed_transition_arrays_before_optimizer(self):
        X = np.zeros((3, 8)); A = np.eye(4)[:3]; X2 = X.copy()
        bad = [(X[:0], A[:0], X2[:0]), (X, A[:2], X2),
               (X, A, X2[:, :7]), (np.full_like(X, np.nan), A, X2),
               (X, np.full_like(A, np.inf), X2)]
        for x, a, y in bad:
            with self.subTest(shape=(x.shape, a.shape, y.shape)):
                with self.assertRaises(ValueError):
                    wj.WorldJEPA(seed=0, ensemble=1).fit(x, a, y, steps=1)


if __name__ == '__main__':
    unittest.main()
