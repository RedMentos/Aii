"""World-JEPA row-vs-column action control: frozen synthetic cohort tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts import world_jepa_action_permutation_control as control
from scripts import world_jepa_digital_shadow as bridge
from scripts import world_jepa_readonly_store as closed
from tests.test_world_jepa_readonly_store import fixture
from v13 import world_jepa as wj
from v13 import world_model as wm


class ActionRowPermutationReview(unittest.TestCase):
    def test_row_shift_breaks_identity_preserves_marginals_and_splits(self):
        A = np.eye(4)[np.arange(8) % 4]
        train, heldout = np.arange(4), np.arange(4, 8)
        tr, te = control.row_shift_actions(A, train, heldout)
        np.testing.assert_array_equal(tr, A[train][[3, 0, 1, 2]])
        np.testing.assert_array_equal(te, A[heldout][[3, 0, 1, 2]])
        np.testing.assert_array_equal(tr.sum(0), A[train].sum(0))
        np.testing.assert_array_equal(te.sum(0), A[heldout].sum(0))
        self.assertFalse(np.array_equal(tr, np.roll(A[train], 1, axis=1)))
        with self.assertRaises(ValueError):
            control.row_shift_actions(A, train, np.array([3, 4, 5, 6]))
        with self.assertRaises(ValueError):
            control.row_shift_actions(A, train, np.array([8, 9]))

    def test_frozen_sqlite_source_cohort_and_nonpromoting_readouts(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'synthetic.sqlite'
            fixture(path, n=64)
            store = closed.ReadOnlyStore(path)
            try:
                rows = wm.transitions(store)
            finally:
                store.close()
            report = control.run_rows(rows, steps=0)
        self.assertEqual(report['source_sha256'],
                         '21bb5a49906676050a1caf755ce441b36a483b3cb8db8d3f1a8a9048e2a7a0bf')
        self.assertEqual(report['train_ids_sha256'],
                         'e526ec41c33f4f639d662e053cbb8757de66737babc76df442a7d1eaed2c164b')
        self.assertEqual(report['heldout_ids_sha256'],
                         'dce3c8c36cf08617c193ea628112964796c23bbd78a5eb353c965396816b0760')
        self.assertEqual((report['n'], report['train_n'], report['heldout_n']), (64, 47, 17))
        self.assertEqual(report['seeds'], [3, 7])
        self.assertEqual(report['row_shift'], 1)
        self.assertGreater(report['row_shift_train_changed_fraction'], 0.)
        self.assertGreater(report['row_shift_heldout_changed_fraction'], 0.)
        self.assertFalse(report['utility_proven'])
        self.assertFalse(report['runtime_wired'])
        self.assertEqual(report['negative_gates_unchanged']['jepa_weight'], 0)
        rendered = json.dumps(report, allow_nan=False)
        self.assertNotIn('synthetic-action-', rendered)
        self.assertNotIn('synthetic-event-', rendered)
        for arm in report['per_seed']:
            for key in ('correct_gain_vs_row_shifted',
                        'correct_gain_vs_column_rotated',
                        'correct_gain_vs_scaled_direct'):
                self.assertTrue(np.isfinite(arm[key]))

    def test_model_training_and_every_readout_use_train_only(self):
        rows = bridge.synthetic_fixture(n=64, seed=20261027)
        data = bridge.make_dataset(rows)
        tr = data['train']
        calls = []

        class FakeModel:
            def __init__(self, seed, ensemble):
                pass
            def fit(self, X, A, X2, steps):
                np.testing.assert_array_equal(X, data['X'][tr])
                np.testing.assert_array_equal(A, data['A'][tr])
                np.testing.assert_array_equal(X2, data['X2'][tr])
                return self
            def predict(self, X, A):
                self_value = X[:, :1] + 2 * A[:, :1]
                return np.tile(self_value, (1, wj.Z)), np.zeros(len(X))

        ridge = bridge._ridge
        with patch.object(control.wj, 'WorldJEPA', FakeModel):
            with patch.object(bridge, '_ridge', wraps=ridge) as spy:
                report = control.run_rows(rows, steps=0)
        self.assertEqual(spy.call_count, 8)
        for call in spy.call_args_list:
            np.testing.assert_array_equal(call.args[1], data['Y'][tr])
        self.assertFalse(report['utility_proven'])

    def test_invalid_step_and_bad_action_refused(self):
        rows = bridge.synthetic_fixture(n=64, seed=20261027)
        for bad in (True, -1, 401, 1.5):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    control.run_rows(rows, steps=bad)
        A = np.eye(4)
        A[0] = np.array([.5, .5, 0., 0.])
        with self.assertRaises(ValueError):
            control.row_shift_actions(A, np.array([0, 1]), np.array([2, 3]))


if __name__ == '__main__':
    unittest.main()
