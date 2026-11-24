"""Matched-state heldout-action synthetic World-JEPA prereg tests."""
import json
import unittest
from unittest.mock import patch

import numpy as np

from scripts import world_jepa_matched_action_cohort as m
from scripts import world_jepa_digital_shadow as bridge
from v13 import world_jepa as wj
from v13 import world_model as wm


class MatchedActionCohortTests(unittest.TestCase):
    def test_exact_fixture_and_one_action_heldout_per_state(self):
        rows = m.fixture()
        self.assertEqual(len(rows), 192)
        self.assertEqual(len({r['action_id'] for r in rows}), 192)
        data = bridge.make_dataset(rows)
        train, heldout = m.split()
        self.assertEqual((len(train), len(heldout)), (144, 48))
        self.assertFalse(set(train) & set(heldout))
        self.assertEqual(sorted(set(train) | set(heldout)), list(range(192)))
        self.assertEqual(list(np.bincount(np.argmax(data['A'][heldout], axis=1),
                                           minlength=4)), [12, 12, 12, 12])
        for i in range(48):
            self.assertEqual(len([j for j in heldout if j // 4 == i]), 1)
            for a in range(4):
                row = rows[4*i+a]
                self.assertEqual(row['a'], wm.ACTIONS[a])
                self.assertEqual(row['action_id'], f'matched-s{i:02d}-a{a}')
                self.assertTrue(all(np.isfinite(row['s'])))
                self.assertTrue(all(np.isfinite(row['y'])))
        self.assertGreater(
            max(rows[0]['y'][0], rows[1]['y'][0], rows[2]['y'][0], rows[3]['y'][0])
            - min(rows[0]['y'][0], rows[1]['y'][0], rows[2]['y'][0], rows[3]['y'][0]), .3)

    def test_three_registered_split_local_shuffles_preserve_counts(self):
        data = bridge.make_dataset(m.fixture())
        train, heldout = m.split()
        for seed in m.SHUFFLE_SEEDS:
            with self.subTest(seed=seed):
                a, b = m.permute_actions(data['A'], train, heldout, seed)
                again = m.permute_actions(data['A'], train, heldout, seed)
                np.testing.assert_array_equal(a, again[0])
                np.testing.assert_array_equal(b, again[1])
                np.testing.assert_array_equal(a.sum(0), data['A'][train].sum(0))
                np.testing.assert_array_equal(b.sum(0), data['A'][heldout].sum(0))
                self.assertGreater(np.mean(np.any(a != data['A'][train], axis=1)), .5)
                self.assertGreater(np.mean(np.any(b != data['A'][heldout], axis=1)), .5)
        with self.assertRaises(ValueError):
            m.permute_actions(data['A'], train, heldout, 999)
        with self.assertRaises(ValueError):
            m.permute_actions(data['A'], train[::-1], heldout, 11)

    def test_train_only_fit_and_ridge_with_fake_model(self):
        data = bridge.make_dataset(m.fixture())
        train, heldout = m.split()
        class FakeModel:
            def __init__(self, seed, ensemble):
                self.seed = seed
            def fit(self, X, A, X2, steps):
                np.testing.assert_array_equal(X, data['X'][train])
                np.testing.assert_array_equal(A, data['A'][train])
                np.testing.assert_array_equal(X2, data['X2'][train])
                return self
            def predict(self, X, A):
                v = X[:, :1] + A[:, :1]
                return np.tile(v, (1, wj.Z)), np.zeros(len(X))
        ridge = bridge._ridge
        with patch.object(m.wj, 'WorldJEPA', FakeModel):
            with patch.object(bridge, '_ridge', wraps=ridge) as spy:
                report = m.run(steps=0)
        self.assertEqual(spy.call_count, 10)
        for call in spy.call_args_list:
            np.testing.assert_array_equal(call.args[1], data['Y'][train])
        self.assertEqual(report['train_n'], 144)
        self.assertEqual(report['heldout_n'], 48)
        self.assertEqual(report['model_seeds'], [3, 7])
        self.assertEqual(report['shuffle_seeds'], [11, 23, 37])
        self.assertEqual(report['heldout_state_action_pairs_seen_in_train'], 0)
        self.assertTrue(report['train_state_overlap_intentional'])
        self.assertFalse(report['utility_proven'])
        self.assertEqual(report['negative_gates_unchanged']['jepa_weight'], 0)
        self.assertNotIn('matched-s', json.dumps(report, allow_nan=False))

    def test_real_model_zero_step_smoke_and_invalid_steps(self):
        report = m.run(steps=0)
        self.assertEqual(report['n'], 192)
        self.assertEqual(len(report['per_model_seed']), 2)
        for arm in report['per_model_seed']:
            self.assertEqual(len(arm['row_shuffle_controls']), 3)
            self.assertTrue(np.isfinite(arm['correct_latent_mae']['pooled']))
        for bad in (-1, 401, True, 1.5):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    m.run(steps=bad)


if __name__ == '__main__':
    unittest.main()
