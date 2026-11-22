import unittest
import numpy as np
from v13.world_jepa_slots_isolated import SlotWorldJEPA

S, OPS = 4, 2   # op 0 sets the slot's flag, op 1 clears it; per-slot features: flag, noise


def world(n, rng, held=()):
    X = np.zeros((n, S, 2)); X[:, :, 0] = rng.integers(0, 2, (n, S)); X[:, :, 1] = rng.normal(size=(n, S))
    A = np.zeros((n, S, OPS+1)); A[:, :, OPS] = 1.; X2 = X.copy()
    for i in range(n):
        while True:
            o, s = rng.integers(0, OPS), rng.integers(0, S)
            if (o, s) not in held: break
        A[i, s] = 0.; A[i, s, o] = 1.; X2[i, s, 0] = 1. if o == 0 else 0.
    return X.reshape(n, -1), A, X2.reshape(n, -1)


class TestSlotWorldJEPA(unittest.TestCase):
    def test_composes_held_out_op_slot_combination(self):
        held = {(0, 3), (1, 0)}
        X, A, X2 = world(1200, np.random.default_rng(0), held)
        m = SlotWorldJEPA(S, seed=1, ensemble=2).fit(X, A, X2, steps=1200).calibrate(X[:200], A[:200], X2[:200])
        rng = np.random.default_rng(5); ok = n = 0
        for _ in range(100):
            x = np.zeros((S, 2)); x[:, 0] = 1-np.eye(S)[3]; x[:, 1] = rng.normal(size=S); x[0, 0] = 1.   # slot 3 clear, slot 0 set
            cands = []
            for o, s in ((0, 3), (1, 0), (0, 1), (1, 2)):
                a = np.zeros((S, OPS+1)); a[:, OPS] = 1.; a[s] = 0.; a[s, o] = 1.; y = x.copy(); y[s, 0] = 1. if o == 0 else 0.; cands.append((a, y))
            Xq = np.repeat(x.reshape(1, -1), 4, 0); Aq = np.array([c[0] for c in cands]); Y = np.array([c[1].reshape(-1) for c in cands])
            p, _ = m.predict(Xq, Aq); zt = m.latent(Y)
            for k in (0, 1):   # the two held-out combinations
                n += 1; ok += int(np.argmin(((zt-p[k])**2).sum((1, 2))) == k)
        self.assertGreater(ok/n, .9)

    def test_untouched_slots_stay_and_confidence_shape(self):
        X, A, X2 = world(600, np.random.default_rng(2))
        m = SlotWorldJEPA(S, seed=3, ensemble=2).fit(X, A, X2, steps=600).calibrate(X[:100], A[:100], X2[:100])
        e = m.slot_errors(X[:100], A[:100], X2[:100]); unt = A[:100].argmax(2) == OPS
        self.assertLess(e[unt].mean(), e[~unt].mean())
        conf, lab = m.confidence(X[:5], A[:5])
        self.assertEqual(conf.shape, (5,)); self.assertEqual(len(lab), 5)
        m.op_counts = np.zeros_like(m.op_counts)
        self.assertTrue((m.confidence(X[:5], A[:5])[0] == 0).all())


class TestIsolatedKernelBoundary(unittest.TestCase):
    def test_frozen_worldjepa_kernel_unchanged_and_not_monkeypatched(self):
        import inspect
        from v13 import world_jepa as frozen
        from v13 import world_jepa_slots_kernels as kernels
        from v13 import world_jepa_slots_isolated as isolated
        self.assertEqual(list(inspect.signature(frozen._init).parameters), ['rng', 'd', 'a'])
        self.assertEqual(list(inspect.signature(kernels._init).parameters),
                         ['rng', 'd', 'a', 'h', 'z', 'hp'])
        self.assertIsNot(frozen._init, kernels._init)
        self.assertIs(isolated._init, kernels._init)
        self.assertEqual(isolated.REVISION, 'run76-z12c-slot-world-jepa-isolated-v1')


if __name__ == '__main__':
    unittest.main()
