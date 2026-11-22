"""Frozen synthetic-only World-JEPA incremental readout contract tests."""
import io
import json
import unittest
from unittest.mock import patch

import numpy as np
from scripts import world_jepa_digital_shadow as bridge
from scripts import world_jepa_incremental_probe as probe
from v13 import world_jepa as wj


class IncrementalProbeTests(unittest.TestCase):
    def setUp(self):
        self.rows = bridge.synthetic_fixture(n=64, seed=20261027)

    def test_smoke_no_authority_no_raw_ids(self):
        report = probe.run_probe(self.rows, steps=0)
        self.assertEqual((report['n'], report['train_n'], report['heldout_n']), (64, 47, 17))
        self.assertEqual(report['seeds'], [3, 7])
        self.assertEqual(report['steps'], 0)
        self.assertFalse(report['runtime_wired'])
        self.assertFalse(report['model_weights_persisted'])
        self.assertFalse(report['utility_proven'])
        self.assertEqual(report['negative_gates_unchanged']['jepa_weight'], 0)
        serialized = json.dumps(report, allow_nan=False)
        self.assertNotIn('synthetic-', serialized)
        self.assertNotIn('action_id', serialized)
        for arm in report['per_seed']:
            for key in ('augmented_mae', 'wrong_action_augmented_mae',
                        'direct_projection_augmented_mae'):
                self.assertTrue(np.isfinite(arm[key]['pooled']))
            self.assertTrue(np.isfinite(arm['pooled_gain_vs_direct']))

    def test_fits_train_only_and_readout_targets_train_only(self):
        data = bridge.make_dataset(self.rows)
        calls = []
        class Fake:
            def __init__(self, seed, ensemble):
                self.seed = seed
            def fit(self, X, A, X2, steps):
                calls.append(('fit', X.copy(), A.copy(), X2.copy(), steps))
                return self
            def predict(self, X, A):
                calls.append(('predict', X.copy(), A.copy()))
                z = X[:, :1] + A[:, :1] + np.arange(wj.Z)[None, :] * .01
                return z, np.zeros(len(X))
        original_ridge = bridge._ridge
        with patch.object(probe.wj, 'WorldJEPA', Fake):
            with patch.object(bridge, '_ridge', wraps=original_ridge) as ridge:
                probe.run_probe(self.rows, steps=0)
        fits = [x for x in calls if x[0] == 'fit']
        self.assertEqual(len(fits), 2)
        for _, X, A, X2, steps in fits:
            np.testing.assert_array_equal(X, data['X'][data['train']])
            np.testing.assert_array_equal(A, data['A'][data['train']])
            np.testing.assert_array_equal(X2, data['X2'][data['train']])
            self.assertEqual(steps, 0)
        self.assertEqual(ridge.call_count, 7)  # direct + 3 augment controls per seed
        for call in ridge.call_args_list:
            np.testing.assert_array_equal(call.args[1], data['Y'][data['train']])
        self.assertTrue(any(x[0] == 'predict' and len(x[1]) == 17 for x in calls))

    def test_train_only_feature_scaling_and_invalid_features(self):
        train = np.tile(np.arange(wj.Z, dtype=float), (4, 1))
        heldout = np.tile(np.arange(wj.Z, dtype=float) + 1000., (2, 1))
        ztr, zte = probe._standardize_train_only(train, heldout)
        self.assertTrue(np.allclose(ztr, 0.))
        self.assertTrue((zte > 1000.).all())
        with self.assertRaises(ValueError):
            probe._standardize_train_only(train, np.full((2, wj.Z), np.nan))
        with self.assertRaises(ValueError):
            probe._standardize_train_only(train[:, :3], heldout)

    def test_invalid_inputs_and_explicit_synthetic_cli(self):
        with self.assertRaises(ValueError):
            probe.run_probe(self.rows, steps=-1)
        with self.assertRaises(ValueError):
            probe.run_probe(self.rows, steps=401)
        with self.assertRaises(ValueError):
            probe.run_probe(self.rows[:31], steps=0)
        with self.assertRaisesRegex(ValueError, 'Only explicit'):
            probe.main([])
        out = io.StringIO()
        with patch.object(probe, 'run_probe', return_value={'scope': 'synthetic', 'utility_proven': False}):
            self.assertEqual(probe.main(['--synthetic-smoke'], stdout=out), 0)
        self.assertEqual(json.loads(out.getvalue())['scope'], 'synthetic')


if __name__ == '__main__':
    unittest.main()
