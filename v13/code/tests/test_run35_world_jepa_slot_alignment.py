"""Run35 synthetic aligned/scrambled matched-parameter SHADOW preflight."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import numpy as np

from v13.world_jepa_slot_candidate import SlotSharedWorldJEPA
from v13.world_jepa_slot_scramble_candidate import (
    ScrambledSlotWorldJEPA, PERM, REVISION, scramble,
)
from scripts.run35_world_jepa_slot_alignment_real import (
    SEEDS, ARGS, run, w7,
)


def tiny():
    rng = np.random.default_rng(41)
    X = rng.normal(size=(48, 60))
    X2 = X + rng.normal(scale=.05, size=X.shape)
    A = np.zeros((48, 12))
    for i in range(48):
        A[i, i % 5] = 1.
        A[i, 6 + (i % 6)] = 1.
    return X, A, X2


def attr(seed, low=False):
    counts = {"own_only": 50, "world_only": 25, "both": 30, "none": 40}
    a = {"n": counts, "own_only_self": .95, "world_only_world": .95,
         "both_world": .85, "none_self": .9}
    b = {"n": counts, "own_only_self": .8, "world_only_world": .8,
         "both_world": .5, "none_self": .75}
    if low:
        a["both_world"] = .5
        a["none_self"] = .65
    return {"seed": seed, "attribution": {"jepa": a, "no_action": b}}


class Run35SlotAlignment(unittest.TestCase):
    def test_fixed_permutation_bijective_and_breaks_locality(self):
        self.assertEqual(len(PERM), 60)
        self.assertEqual(set(PERM.tolist()), set(range(60)))
        self.assertTrue(REVISION.startswith("run35-slot-alignment"))
        x = np.arange(60, dtype=float).reshape(1, 60)
        y = scramble(x)
        self.assertEqual(y.shape, x.shape)
        np.testing.assert_array_equal(y[0], PERM)
        self.assertTrue(all(len(set(PERM.reshape(6, 10)[i] // 10)) > 1
                            for i in range(6)))

    def test_invalid_observation_rejected_without_core(self):
        m = ScrambledSlotWorldJEPA()
        for bad in (np.zeros((2, 59)), np.full((2, 60), np.nan), [1, 2]):
            with self.subTest(shape=np.shape(bad)):
                with self.assertRaises(ValueError):
                    m.fit(bad, np.zeros((2, 12)), np.zeros((2, 60)), steps=2)
        self.assertFalse(hasattr(m, "core"))
        with self.assertRaisesRegex(ValueError, "RUN35_NOT_FITTED"):
            m.latent(np.zeros((2, 60)))

    def test_actual_numpy_fit_same_core_parameter_shapes_and_interface(self):
        X, A, X2 = tiny()
        a = SlotSharedWorldJEPA(seed=7, ensemble=2).fit(X, A, X2, steps=2)
        b = ScrambledSlotWorldJEPA(seed=7, ensemble=2).fit(X, A, X2, steps=2)
        self.assertEqual({k: v.shape for k, v in a.core.enc.items()},
                         {k: v.shape for k, v in b.core.core.enc.items()})
        self.assertEqual({k: v.shape for k, v in a.core.preds[0].items()},
                         {k: v.shape for k, v in b.core.core.preds[0].items()})
        self.assertEqual(len(a.zsd), 96)
        self.assertEqual(len(b.zsd), 96)
        self.assertEqual(b.latent(X).shape, (48, 96))
        pred, spread = b.predict(X, A)
        self.assertEqual(pred.shape, (48, 96))
        self.assertEqual(spread.shape, (48,))
        conf, labels = b.confidence(X, A)
        self.assertEqual(conf.shape, (48,))
        self.assertEqual(len(labels), 48)
        self.assertTrue(np.isfinite(conf).all())
        self.assertEqual(b.ood(X).shape, (48,))
        self.assertIn("collapsed", b.collapse_stats(X2))
        self.assertTrue(np.isfinite(pred).all())

    def test_failed_refit_keeps_prior_published_core(self):
        X, A, X2 = tiny()
        m = ScrambledSlotWorldJEPA(seed=7, ensemble=1).fit(X, A, X2, steps=2)
        core = m.core
        with self.assertRaises(ValueError):
            m.fit(X, A, X2[:, :-1], steps=2)
        self.assertIs(m.core, core)

    def test_w7_frozen_thresholds_and_class_counts(self):
        good = [attr(seed) for seed in SEEDS]
        gates, summary = w7(good)
        self.assertTrue(all(gates.values()))
        self.assertEqual(len(summary["per_seed"]), 3)
        bad = [attr(seed, low=True) for seed in SEEDS]
        gates2, _ = w7(bad)
        self.assertFalse(gates2["W7a_both_world_action_gain"])
        self.assertFalse(gates2["W7b_none_self_action_gain"])
        self.assertFalse(gates2["W7c_four_class_macro_action_gain"])
        good[0]["attribution"]["jepa"]["n"]["both"] = 14
        with self.assertRaisesRegex(ValueError, "RUN35_W7_CLASS_SUPPORT_RED"):
            w7(good)

    def test_registered_cohort_mutation_rejected_before_file_io(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.json"
            work = Path(tmp) / "work"
            with self.assertRaisesRegex(ValueError, "RUN35_REGISTERED_COHORT_MUTATION_RED"):
                run(out, work, seeds=(301, 302, 304))
            self.assertFalse(out.exists())
            self.assertFalse(work.exists())
            with self.assertRaisesRegex(ValueError, "RUN35_REGISTERED_COHORT_MUTATION_RED"):
                run(out, work, args={**ARGS, "steps": 2})
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
