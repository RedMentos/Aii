"""Run28 slot-shared World-JEPA software tests; no real-world or Redmi proof."""
from __future__ import annotations

import unittest
import numpy as np

from v13.world_jepa_slot_candidate import (
    SlotSharedWorldJEPA, _decode, _local_actions, FULL_ACTIONS,
    LOCAL_ACTIONS, SLOTS, FEATURES, REVISION,
)


def action(op, slot=None):
    a = np.zeros(LOCAL_ACTIONS + SLOTS)
    a[op] = 1.
    if slot is not None:
        a[LOCAL_ACTIONS + slot] = 1.
    return a


def toy(n=96, seed=13):
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, (n, SLOTS * FEATURES))
    A = np.zeros((n, LOCAL_ACTIONS + SLOTS))
    X2 = X.copy()
    for i in range(n):
        op = i % 5
        slot = (i // 5) % 5  # intentionally never touch slot 5
        A[i] = action(op, slot)
        X2[i, slot * FEATURES:(slot+1) * FEATURES] += (op+1) * .1
    return X, A, X2


class SlotWorldJepaRun28(unittest.TestCase):
    def test_exact_full_action_decode_and_zero_control(self):
        A = np.stack([action(0, 2), action(4, 5), action(5), np.zeros(12)])
        ids = _decode(A)
        self.assertEqual(ids.tolist(), [2, 29, 30, -1])
        local = _local_actions(ids)
        self.assertEqual(local.shape, (4, 6, 6))
        self.assertEqual(local[0, 2, 0], 1)
        self.assertEqual(local[0, 2, 5], 0)
        self.assertTrue(np.all(local[0, [0, 1, 3, 4, 5], 5] == 1))
        self.assertTrue(np.all(local[2, :, 5] == 1))
        self.assertTrue(np.all(local[3] == 0))

    def test_invalid_action_onehot_and_slot_fail_closed(self):
        for bad in (action(0), action(5, 2), np.ones(12), np.full(12, np.nan)):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    _decode(np.array([bad]))
        self.assertEqual(FULL_ACTIONS, 31)
        self.assertTrue(REVISION.startswith("run28-slot-shared"))

    def test_fit_latent_predict_confidence_shapes_and_unseen_veto(self):
        X, A, X2 = toy()
        m = SlotSharedWorldJEPA(seed=7, ensemble=2).fit(X, A, X2, steps=8, log_every=4)
        self.assertEqual(m.zsd.shape, (96,))
        z = m.latent(X[:3])
        pred, spread = m.predict(X[:3], A[:3])
        self.assertEqual(z.shape, (3, 96))
        self.assertEqual(pred.shape, (3, 96))
        self.assertEqual(spread.shape, (3,))
        self.assertTrue(np.isfinite(z).all())
        self.assertTrue(np.isfinite(pred).all())
        self.assertTrue(np.isfinite(spread).all())
        self.assertEqual(int(m._full_counts[4 * 6 + 5]), 0)
        held = np.array([action(4, 5)])
        conf, labels = m.confidence(X[:1], held, counts=[1000000])
        self.assertEqual(conf.tolist(), [0.])
        self.assertEqual(labels, ["SIMULATION_UNCERTAIN"])
        zero, labels0 = m.confidence(X[:1], np.zeros((1, 12)))
        self.assertEqual(zero.tolist(), [0.])
        self.assertEqual(labels0, ["SIMULATION_UNCERTAIN"])

    def test_unfitted_and_malformed_fit_never_publish(self):
        X, A, X2 = toy()
        m = SlotSharedWorldJEPA(seed=9, ensemble=1)
        with self.assertRaisesRegex(ValueError, "NOT_FITTED"):
            m.latent(X[:1])
        bad = A.copy()
        bad[0, 0] = np.nan
        with self.assertRaises(ValueError):
            m.fit(X, bad, X2, steps=2)
        self.assertFalse(hasattr(m, "core"))
        with self.assertRaises(ValueError):
            m.fit(X, A, X2[:, :-1], steps=2)
        self.assertFalse(hasattr(m, "core"))

    def test_bad_refit_keeps_last_complete_candidate(self):
        X, A, X2 = toy()
        m = SlotSharedWorldJEPA(seed=3, ensemble=1).fit(X, A, X2, steps=4)
        old = m.core
        with self.assertRaises(ValueError):
            m.fit(X, A[:5], X2, steps=4)
        self.assertIs(m.core, old)
        conf, labels = m.confidence(X[:1], A[:1])
        self.assertEqual(conf.tolist(), [0.])
        self.assertEqual(labels, ["SIMULATION_UNCERTAIN"])

    def test_confidence_caller_cannot_create_unseen_support(self):
        X, A, X2 = toy()
        m = SlotSharedWorldJEPA(seed=4, ensemble=2).fit(X, A, X2, steps=4)
        query = np.array([action(3, 5)])
        for count in (0, 1, 100, 100000):
            c, labels = m.confidence(X[:1], query, counts=[count])
            self.assertEqual(c.tolist(), [0.])
            self.assertEqual(labels, ["SIMULATION_UNCERTAIN"])
        c, labels = m.confidence(X[:1], A[:1], counts=[float("nan")])
        self.assertEqual(c.tolist(), [0.])
        self.assertEqual(labels, ["SIMULATION_UNCERTAIN"])


if __name__ == "__main__":
    unittest.main()
