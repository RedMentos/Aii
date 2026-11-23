"""World-JEPA heldout-only mismatch: synthetic, fixed-readout, no gate proof."""
import io
import json
import unittest
from unittest.mock import patch

import numpy as np

from scripts import world_jepa_digital_shadow as bridge
from scripts import world_jepa_heldout_action_readout_20261028 as review
from v13 import world_jepa as wj


class FixedReadoutHeldoutAction(unittest.TestCase):
    def setUp(self):
        self.rows = bridge.synthetic_fixture(n=64, seed=20261027)
        self.data = bridge.make_dataset(self.rows)

    def test_synthetic_zero_step_is_finite_reproducible_and_nonpromoting(self):
        first = review.run_rows(self.rows, steps=0)
        second = review.run_rows(self.rows, steps=0)
        self.assertEqual(first, second)
        self.assertEqual(first['seeds'], [3, 7])
        self.assertEqual((first['train_n'], first['heldout_n']), (47, 17))
        self.assertEqual(first['source_sha256'], self.data['source_sha256'])
        self.assertEqual(first['heldout_ids_sha256'], self.data['heldout_ids_sha256'])
        self.assertTrue(first['readout_frozen_for_heldout_controls'])
        self.assertGreater(first['heldout_row_mismatch_changed_fraction'], 0.)
        self.assertTrue(first['heldout_row_marginals_preserved'])
        self.assertFalse(first['utility_proven'])
        self.assertFalse(first['runtime_wired'])
        self.assertEqual(first['negative_gates_unchanged']['jepa_weight'], 0)
        text = json.dumps(first, allow_nan=False)
        self.assertNotIn('synthetic-', text)
        for row in first['per_seed']:
            for key in ('gain_vs_direct', 'gain_vs_heldout_row_mismatch',
                        'gain_vs_heldout_column_mismatch'):
                self.assertTrue(np.isfinite(row[key]))

    def test_training_and_ridge_never_use_wrong_or_heldout_actions(self):
        data = self.data
        tr, te = data['train'], data['heldout']
        calls = []

        class FakeModel:
            def __init__(self, seed, ensemble):
                self.seed = seed
            def fit(self, X, A, X2, steps):
                np.testing.assert_array_equal(X, data['X'][tr])
                np.testing.assert_array_equal(A, data['A'][tr])
                np.testing.assert_array_equal(X2, data['X2'][tr])
                calls.append(('fit', self.seed, A.copy()))
                return self
            def predict(self, X, A):
                calls.append(('predict', self.seed, A.copy()))
                v = X[:, :1] + 2 * A[:, :1]
                return np.tile(v, (1, wj.Z)), np.zeros(len(X))

        original_ridge = bridge._ridge
        with patch.object(review.wj, 'WorldJEPA', FakeModel):
            with patch.object(bridge, '_ridge', wraps=original_ridge) as spy:
                result = review.run_rows(self.rows, steps=0)
        self.assertEqual(spy.call_count, 3)  # one direct + one fixed per seed
        for call in spy.call_args_list:
            np.testing.assert_array_equal(call.args[1], data['Y'][tr])
        for seed in (3, 7):
            sequence = [a for kind, s, a in calls if kind == 'predict' and s == seed]
            self.assertEqual(len(sequence), 4)
            np.testing.assert_array_equal(sequence[0], data['A'][tr])
            np.testing.assert_array_equal(sequence[1], data['A'][te])
            self.assertFalse(np.array_equal(sequence[2], data['A'][te]))
            self.assertFalse(np.array_equal(sequence[3], data['A'][te]))
            np.testing.assert_array_equal(sequence[2].sum(0), data['A'][te].sum(0))
        self.assertFalse(result['utility_proven'])

    def test_no_heldout_action_change_rejected_before_training(self):
        rows = [dict(row, a='simple') for row in self.rows]
        with self.assertRaisesRegex(ValueError, 'no changed rows'):
            review.run_rows(rows, steps=0)

    def test_invalid_steps_and_nonfinite_predicted_latents_rejected(self):
        for value in (True, -1, 401, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                review.run_rows(self.rows, steps=value)

        class BadModel:
            def __init__(self, seed, ensemble):
                pass
            def fit(self, X, A, X2, steps):
                return self
            def predict(self, X, A):
                return np.full((len(X), wj.Z), np.nan), np.zeros(len(X))
        with patch.object(review.wj, 'WorldJEPA', BadModel):
            with self.assertRaises(ValueError):
                review.run_rows(self.rows, steps=0)

    def test_cli_requires_synthetic_opt_in(self):
        with self.assertRaises(ValueError):
            review.main([], stdout=io.StringIO())
        out = io.StringIO()
        self.assertEqual(review.main(['--synthetic-smoke', '--steps', '0'], stdout=out), 0)
        self.assertFalse(json.loads(out.getvalue())['utility_proven'])


if __name__ == '__main__':
    unittest.main()
