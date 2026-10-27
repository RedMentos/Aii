"""Software-only preregistered World-JEPA heldout harness contract tests."""
import copy
import tempfile
import unittest
from pathlib import Path
import numpy as np

from scripts import world_jepa_heldout_ablation as h
from v13 import world_jepa as wj


class WorldJEPAHeldoutAblationTests(unittest.TestCase):
    def test_exact_registered_source_hashes_and_disjoint_rows(self):
        tr = h.make_rows(h.TRAIN_N, h.TRAIN_SEED)
        te = h.make_rows(h.TEST_N, h.TEST_SEED)
        self.assertTrue(h.verify_rows(tr, h.TRAIN_N, h.TRAIN_SHA))
        self.assertTrue(h.verify_rows(te, h.TEST_N, h.TEST_SHA))
        self.assertEqual([sum(row['action'] == k for row in tr) for k in range(4)],
                         [249, 266, 246, 239])
        self.assertEqual([sum(row['action'] == k for row in te) for k in range(4)],
                         [64, 68, 61, 47])
        self.assertFalse({str(r) for r in tr} & {str(r) for r in te})

    def test_tampered_source_or_partial_cohort_is_rejected(self):
        tr = h.make_rows(h.TRAIN_N, h.TRAIN_SEED)
        bad = copy.deepcopy(tr)
        bad[0]['bits'][0] ^= 1
        with self.assertRaisesRegex(ValueError, 'SHA/size'):
            h.verify_rows(bad, h.TRAIN_N, h.TRAIN_SHA)
        with self.assertRaisesRegex(ValueError, 'SHA/size'):
            h.verify_rows(tr[:-1], h.TRAIN_N, h.TRAIN_SHA)

    def test_heldout_scorer_finite_and_target_tamper_refused(self):
        tr = h.make_rows(40, 501)
        te = h.make_rows(10, 502)
        X, A, X2, _ = h.arrays(tr)
        Xe, Ae, X2e, act = h.arrays(te)
        model = wj.WorldJEPA(seed=1, ensemble=2).fit(X, A, X2, steps=0)
        score = h.score_model(model, Xe, Ae, X2e, act)
        for k in ('ensemble_mean_mse', 'first_member_mse',
                  'wrong_action_mse', 'persistence_mse'):
            self.assertTrue(np.isfinite(score[k]), k)
            self.assertGreaterEqual(score[k], 0.)
        altered = X2e.copy()
        altered[0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, 'Invalid heldout'):
            h.score_model(model, Xe, Ae, altered, act)
        with self.assertRaisesRegex(ValueError, 'Invalid heldout'):
            h.score_model(model, Xe, np.roll(Ae, 1, axis=1), X2e, act)

    def test_pooled_gates_are_explicit_and_not_automatic_promotion(self):
        bad = [{'seed': s, 'ensemble_mean_mse': 1., 'first_member_mse': 1.01,
                'wrong_action_mse': 1.02, 'persistence_mse': 1.02}
               for s in h.MODEL_SEEDS]
        out = h.summarize(bad)
        self.assertEqual(out['ensemble_mean_gain_criterion'], 'FAIL')
        self.assertEqual(out['synthetic_action_signal_criterion'], 'FAIL')
        good = [{**r, 'ensemble_mean_mse': .7} for r in bad]
        out = h.summarize(good)
        self.assertEqual(out['ensemble_mean_gain_criterion'], 'PASS')
        self.assertEqual(out['synthetic_action_signal_criterion'], 'PASS')
        self.assertTrue(out['gates_are_synthetic_only'])
        with self.assertRaisesRegex(ValueError, 'seed'):
            h.summarize(good[:-1])

    def test_invalid_action_indices_fail_closed_before_numpy_indexing(self):
        tr = h.make_rows(40, 501)
        te = h.make_rows(10, 502)
        X, A, X2, _ = h.arrays(tr)
        Xe, Ae, X2e, action = h.arrays(te)
        model = wj.WorldJEPA(seed=1, ensemble=2).fit(X, A, X2, steps=0)
        self.assertEqual(action[5], 3)
        self.assertTrue(np.isfinite(h.score_model(model, Xe, Ae, X2e, action)['ensemble_mean_mse']))
        for bad in (
            np.where(np.arange(len(action)) == 5, -1, action),
            np.where(np.arange(len(action)) == 5, 4, action),
            action.astype(float),
            action.astype(bool),
            action.astype(object),
            np.where(np.arange(len(action)) == 5, 4, action).astype(np.uint64),
            action.reshape(-1, 1),
        ):
            with self.subTest(bad_dtype=str(bad.dtype), bad_shape=bad.shape):
                with self.assertRaisesRegex(ValueError, 'Invalid heldout action indices'):
                    h.score_model(model, Xe, Ae, X2e, bad)

    def test_explicit_execution_flag_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'receipt.json'
            with self.assertRaisesRegex(ValueError, 'Explicit'):
                h.main(['--out', str(out)])
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
