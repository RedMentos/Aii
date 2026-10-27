"""Fair direct-feature scaling and action-control research-only tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scripts import world_jepa_fair_baseline as fair
from scripts import world_jepa_digital_shadow as bridge
from scripts import world_jepa_readonly_store as closed
from tests.test_world_jepa_readonly_store import fixture
from v13 import world_jepa as wj
from v13 import world_model as wm


class FairBaselineTests(unittest.TestCase):
    def test_direct_scaler_train_only_and_intercept_preserved(self):
        train = np.array([[1., 0., 2.], [1., 2., 4.]])
        heldout = np.array([[1., 1000., 2000.]])
        tr, te = fair._scaled_direct(train, heldout)
        np.testing.assert_allclose(tr[:, 0], 1.)
        np.testing.assert_allclose(te[:, 0], 1.)
        np.testing.assert_allclose(tr[:, 1:].mean(0), 0., atol=1e-12)
        self.assertTrue((te[:, 1:] > 900.).all())
        with self.assertRaises(ValueError):
            fair._scaled_direct(train, np.array([[0., 1., 2.]]))
        with self.assertRaises(ValueError):
            fair._scaled_direct(train, np.array([[1., float('nan'), 2.]]))

    def test_frozen_synthetic_sqlite_cohort_no_ids_no_authority(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'synthetic.sqlite'
            fixture(path, n=64)
            store = closed.ReadOnlyStore(path)
            try:
                rows = wm.transitions(store)
            finally:
                store.close()
            report = fair.run_rows(rows, steps=0)
        self.assertEqual(report['source_sha256'], '21bb5a49906676050a1caf755ce441b36a483b3cb8db8d3f1a8a9048e2a7a0bf')
        self.assertEqual(report['train_ids_sha256'], 'e526ec41c33f4f639d662e053cbb8757de66737babc76df442a7d1eaed2c164b')
        self.assertEqual(report['heldout_ids_sha256'], 'dce3c8c36cf08617c193ea628112964796c23bbd78a5eb353c965396816b0760')
        self.assertEqual((report['n'], report['train_n'], report['heldout_n']), (64,47,17))
        self.assertEqual(report['seeds'], [3,7])
        self.assertEqual(report['steps'], 0)
        self.assertFalse(report['utility_proven'])
        self.assertFalse(report['runtime_wired'])
        self.assertEqual(report['negative_gates_unchanged']['jepa_weight'], 0)
        rendered = json.dumps(report, allow_nan=False)
        self.assertNotIn('synthetic-action-', rendered)
        self.assertNotIn('synthetic-event-', rendered)
        for arm in report['per_seed']:
            self.assertTrue(np.isfinite(arm['gain_vs_scaled_direct']))
            self.assertTrue(np.isfinite(arm['gain_vs_wrong_action']))
            self.assertTrue(np.isfinite(arm['gain_vs_projection']))

    def test_all_ridge_fits_use_train_targets_only(self):
        rows = bridge.synthetic_fixture(n=64, seed=20261027)
        data = bridge.make_dataset(rows)
        calls = []
        class Fake:
            def __init__(self, seed, ensemble):
                pass
            def fit(self, X, A, X2, steps):
                np.testing.assert_array_equal(X, data['X'][data['train']])
                np.testing.assert_array_equal(A, data['A'][data['train']])
                np.testing.assert_array_equal(X2, data['X2'][data['train']])
                return self
            def predict(self, X, A):
                return np.tile(X[:, :1] + A[:, :1], (1, wj.Z)), np.zeros(len(X))
        ridge = bridge._ridge
        with patch.object(fair.wj, 'WorldJEPA', Fake):
            with patch.object(bridge, '_ridge', wraps=ridge) as spy:
                fair.run_rows(rows, steps=0)
        self.assertEqual(spy.call_count, 7)
        for call in spy.call_args_list:
            np.testing.assert_array_equal(call.args[1], data['Y'][data['train']])

    def test_invalid_steps_refused(self):
        rows = bridge.synthetic_fixture(n=64, seed=20261027)
        for bad in (-1, 401, True, 1.5):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    fair.run_rows(rows, steps=bad)


if __name__ == '__main__':
    unittest.main()
