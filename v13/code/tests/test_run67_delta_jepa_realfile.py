"""Run67 delta-inverse candidate: gradient, cohort, negative-gate checks."""
import random
import unittest
from unittest import mock

import numpy as np

from scripts import run60_z12b_slotlocal_real_file_baseline as parent
from scripts import run63_z12b_factorized_real_file_baselines as factor
from scripts import run67_delta_jepa_realfile as probe
from scripts import z12b_world_jepa as original
from v13 import world_jepa as frozen


class DeltaInverseGradients(unittest.TestCase):
    def test_analytic_gradient_against_central_finite_difference(self):
        rng = np.random.default_rng(7)
        enc, _ = frozen._init(rng, 5, 11)
        inv = probe._init_delta_inv(rng, 11)
        x, x2 = rng.normal(size=(4, 5)), rng.normal(size=(4, 5))
        a = np.zeros((4, 11))
        a[np.arange(4), [0, 1, 2, 3]] = 1.
        a[np.arange(4), [5, 6, 7, 8]] = 1.
        loss, ge, gi = probe.delta_inverse_loss_grads(enc, inv, x, x2, a)
        self.assertTrue(np.isfinite(loss))
        self.assertAlmostEqual(float(np.max(np.abs(ge['b2']))), 0., places=12)
        eps = 1e-5
        for params, grads in ((enc, ge), (inv, gi)):
            for key in params:
                for idx in (np.ndindex(params[key].shape)):
                    old = params[key][idx]
                    params[key][idx] = old+eps
                    plus = probe.delta_inverse_loss_grads(enc, inv, x, x2, a)[0]
                    params[key][idx] = old-eps
                    minus = probe.delta_inverse_loss_grads(enc, inv, x, x2, a)[0]
                    params[key][idx] = old
                    self.assertAlmostEqual(
                        (plus-minus)/(2*eps), grads[key][idx],
                        delta=2e-5, msg=f'{key}:{idx}')

    def test_delta_translation_invariance(self):
        rng = np.random.default_rng(8)
        enc, _ = frozen._init(rng, 6, 11)
        inv = probe._init_delta_inv(rng, 11)
        x, x2 = rng.normal(size=(3, 6)), rng.normal(size=(3, 6))
        a = np.zeros((3, 11))
        original_loss = probe.delta_inverse_loss_grads(enc, inv, x, x2, a)[0]
        enc['b2'] += 17.25
        shifted_loss = probe.delta_inverse_loss_grads(enc, inv, x, x2, a)[0]
        self.assertAlmostEqual(original_loss, shifted_loss, places=12)


class Run67RealFileDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = probe.run()

    def test_registered_cohort_and_negative_gates(self):
        r = self.report
        self.assertEqual(r['schema'], probe.SCHEMA)
        self.assertEqual(r['seeds'], [271, 277, 281])
        self.assertEqual(r['n_train_per_seed'], 240)
        self.assertEqual(r['n_holdout_per_seed'], 60)
        self.assertEqual(r['steps'], 200)
        self.assertTrue(r['file_actions_executed'])
        self.assertTrue(r['jepa_training_executed'])
        for key in ('jepa_only_utility_proven', 'native_model_executed',
                    'model_weights_published', 'counterfactual_causality_proven',
                    'confidence_measured', 'source_disjointness_verified',
                    'phone_measured', 'learning_gate_pass',
                    'whole_system_complete'):
            self.assertFalse(r[key])
        self.assertEqual(r['jepa_weight'], 0)
        self.assertEqual(r['age_authority'], 0)

    def test_real_rows_all_arms_and_collapse_diagnostics(self):
        for row in self.report['reports']:
            self.assertEqual(row['n_train'], 240)
            self.assertEqual(row['n_holdout'], 60)
            self.assertEqual(row['test_action_count'], 4)
            self.assertEqual(len(row['heldout_action_indices']), 4)
            for key in ('train_rows_sha256', 'test_rows_sha256',
                        'shuffled_train_permutation_sha256'):
                self.assertRegex(row[key], r'^[a-f0-9]{64}$')
            self.assertEqual(set(row['metrics']), set(probe.ARM_NAMES))
            self.assertEqual(set(row['supervised_baseline_metrics']),
                             set(factor.MODEL_NAMES))
            self.assertEqual(set(row['delta_train_collapse_stats']),
                             {'delta_observed', 'delta_zero',
                              'delta_shuffled_train'})
            for value in row['metrics'].values():
                self.assertTrue(np.isfinite(value['overall_mse']))
                self.assertTrue(np.isfinite(value['target_slot_mse']))
                self.assertGreaterEqual(value['overall_mse'], 0.)
            for value in row['delta_train_collapse_stats'].values():
                self.assertTrue(np.isfinite(value['effective_rank']))
                self.assertTrue(np.isfinite(value['min_std']))
                self.assertGreaterEqual(value['effective_rank'], 0.)
                self.assertGreaterEqual(value['min_std'], 0.)

    def test_reproducible_registered_real_file_cohort(self):
        self.assertEqual(self.report, probe.run())

    def test_train_only_readout_receives_no_heldout_target(self):
        calls = []
        def fake(model, x, a, x2, xt, at, *, seed):
            self.assertEqual(x.shape, x2.shape)
            self.assertEqual(x.shape[0], 240)
            self.assertEqual(xt.shape[0], 60)
            self.assertEqual(a.shape, (240, 11))
            self.assertEqual(at.shape, (60, 11))
            calls.append((model, a.copy(), at.copy()))
            return xt.copy(), ({'effective_rank': 1., 'min_std': 1.}
                               if model is probe.DeltaWorldJEPA else None)
        with mock.patch.object(probe, '_fit_readout', side_effect=fake):
            row = probe._seed(271)
        self.assertEqual(len(calls), 5)
        self.assertTrue(np.array_equal(calls[1][1], np.zeros((240, 11))))
        self.assertTrue(np.array_equal(calls[3][1], np.zeros((240, 11))))
        self.assertFalse(np.array_equal(calls[2][1], calls[4][1]))
        self.assertEqual(row['n_holdout'], 60)

    def test_invalid_cohort_refused_before_file_actions(self):
        with mock.patch.object(parent, '_rows',
                               side_effect=AssertionError('unexpected files')):
            for kwargs in ({'seeds': (271,)}, {'seeds': [271, 277, 281]},
                           {'n_train': 12}, {'n_test': 12}, {'steps': 201}):
                with self.assertRaises(PermissionError):
                    probe.run(**kwargs)


if __name__ == '__main__':
    unittest.main()
