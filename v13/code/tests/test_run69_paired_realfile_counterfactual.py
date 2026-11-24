"""Run69 paired real-file action counterfactual discrimination regressions."""
import random
import unittest
from unittest import mock

import numpy as np

from scripts import run60_z12b_slotlocal_real_file_baseline as parent
from scripts import run69_paired_realfile_counterfactual as probe


class PairedScoreControls(unittest.TestCase):
    def setUp(self):
        self.y = np.zeros((probe.N_STATES, 4, parent.FEATURES))
        for i in range(4):
            self.y[:, i, i] = float(i+1)

    def test_oracle_perfect_and_action_blind_all_ties(self):
        oracle = probe._score(self.y, self.y)
        blind = probe._score(np.zeros_like(self.y), self.y)
        self.assertEqual(oracle['informative_pairs'], probe.N_STATES*6)
        self.assertEqual(oracle['correct'], oracle['informative_pairs'])
        self.assertEqual(oracle['wrong'], 0)
        self.assertEqual(oracle['tied'], 0)
        self.assertEqual(blind['correct'], 0)
        self.assertEqual(blind['wrong'], 0)
        self.assertEqual(blind['tied'], blind['informative_pairs'])
        self.assertEqual(blind['pair_tie_fraction'], 1.)

    def test_swapped_action_predictions_do_not_pass_oracle(self):
        swapped = self.y.copy()
        swapped[:, [0, 1]] = swapped[:, [1, 0]]
        result = probe._score(swapped, self.y)
        self.assertGreater(result['wrong'], 0)
        self.assertLess(result['strict_pair_accuracy'], 1.)

    def test_identical_actual_outcomes_excluded_not_claimed_correct(self):
        y = self.y.copy()
        y[:, 1] = y[:, 0]
        result = probe._score(y, y)
        self.assertEqual(result['indistinguishable_pairs'], probe.N_STATES)
        self.assertEqual(result['informative_pairs'], probe.N_STATES*5)
        self.assertEqual(result['correct'], result['informative_pairs'])

    def test_malformed_nonfinite_and_wrong_state_count_fail_closed(self):
        for bad in (self.y[:1], np.full_like(self.y, np.nan),
                    np.zeros((probe.N_STATES, 3, parent.FEATURES))):
            with self.assertRaises(ValueError):
                probe._score(bad, bad)


class PairedRealFileSourceTests(unittest.TestCase):
    def test_registered_source_is_deterministic_and_four_real_actions(self):
        seed = probe.SEEDS[0]
        held = tuple(sorted(random.Random(seed).sample(parent.NON_NOOP, 4)))
        one = probe._paired_states(seed, held)
        two = probe._paired_states(seed, held)
        self.assertEqual(probe._digest_paired(one), probe._digest_paired(two))
        self.assertEqual(len(one), probe.N_STATES)
        self.assertEqual(sum(len(r['candidates']) for r in one),
                         probe.N_STATES*4)
        self.assertTrue(all(tuple(c[0] for c in row['candidates']) == held
                            for row in one))
        self.assertTrue(any(c[3] for row in one for c in row['candidates']))
        for row in one:
            for a, x2, ok, changed in row['candidates']:
                self.assertEqual(x2.shape, row['x'].shape)
                self.assertEqual(changed, not np.array_equal(row['x'], x2))
                self.assertIs(type(ok), bool)

    def test_unregistered_parameters_fail_before_file_actions(self):
        with mock.patch.object(parent, '_rows',
                               side_effect=AssertionError('unexpected files')):
            for kwargs in ({'seeds': (283,)},
                           {'seeds': [283, 293, 307]},
                           {'n_train': 12}, {'n_states': 12},
                           {'steps': 201}):
                with self.assertRaises(PermissionError):
                    probe.run(**kwargs)

    def test_paired_generator_rejects_unregistered_cohort(self):
        seed = probe.SEEDS[0]
        held = tuple(sorted(random.Random(seed).sample(parent.NON_NOOP, 4)))
        for args in ((seed, held, 25), (seed, held[:3], 24),
                     (999, held, 24)):
            with self.assertRaises(PermissionError):
                probe._paired_states(*args)


class Run69RegisteredResult(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = probe.run()

    def test_registered_counts_and_negative_gates(self):
        r = self.report
        self.assertEqual(r['schema'], probe.SCHEMA)
        self.assertEqual(r['seeds'], [283, 293, 307])
        self.assertEqual(r['train_rows_per_seed'], 240)
        self.assertEqual(r['paired_source_states_per_seed'], 24)
        self.assertEqual(r['steps'], 200)
        self.assertTrue(r['file_actions_executed'])
        self.assertTrue(r['jepa_training_executed'])
        self.assertTrue(r['oracle_uses_heldout_targets_diagnostic_only'])
        for key in ('native_model_executed', 'model_weights_published',
                    'counterfactual_causality_proven',
                    'jepa_only_utility_proven', 'confidence_measured',
                    'source_disjointness_verified', 'phone_measured',
                    'learning_gate_pass', 'whole_system_complete'):
            self.assertFalse(r[key], key)
        self.assertEqual(r['age_authority'], 0)
        self.assertEqual(r['jepa_weight'], 0)

    def test_all_arms_same_informative_pairs_and_controls(self):
        for row in self.report['reports']:
            self.assertEqual(row['train_rows'], 240)
            self.assertEqual(row['paired_source_states'], 24)
            self.assertEqual(row['real_candidate_file_actions'], 96)
            self.assertEqual(len(row['heldout_action_indices']), 4)
            self.assertEqual(set(row['metrics']), set(probe.MODEL_NAMES))
            self.assertRegex(row['train_rows_sha256'], r'^[0-9a-f]{64}$')
            self.assertRegex(row['paired_rows_sha256'], r'^[0-9a-f]{64}$')
            informative = row['metrics']['oracle_diagnostic']['informative_pairs']
            self.assertGreater(informative, 0)
            for name, metric in row['metrics'].items():
                self.assertEqual(metric['informative_pairs'], informative)
                self.assertEqual(
                    metric['correct']+metric['wrong']+metric['tied'],
                    informative)
                self.assertTrue(np.isfinite(metric['overall_mse']))
                self.assertGreaterEqual(metric['overall_mse'], 0.)
            oracle = row['metrics']['oracle_diagnostic']
            blind = row['metrics']['persistence_blind']
            zero = row['metrics']['delta_zero']
            self.assertEqual(oracle['correct'], informative)
            self.assertEqual(oracle['wrong']+oracle['tied'], 0)
            self.assertEqual(blind['tied'], informative)
            self.assertEqual(zero['tied'], informative)
        for name, aggregate in self.report['aggregate'].items():
            self.assertEqual(aggregate['informative_pairs'],
                             sum(row['metrics'][name]['informative_pairs']
                                 for row in self.report['reports']))

    def test_source_reproducibility_without_rerunning_models(self):
        for row in self.report['reports']:
            seed = row['seed']
            held = tuple(row['heldout_action_indices'])
            self.assertEqual(row['paired_rows_sha256'],
                             probe._digest_paired(probe._paired_states(seed, held)))


if __name__ == '__main__':
    unittest.main()
