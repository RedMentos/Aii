"""Run71 latent-only paired real-file candidate and negative-gate tests."""
import random
import unittest
from unittest import mock

import numpy as np

from scripts import run60_z12b_slotlocal_real_file_baseline as parent
from scripts import run71_paired_latent_only_realfile as probe
from v13 import world_jepa as frozen


class LatentOnlyPairControls(unittest.TestCase):
    def setUp(self):
        self.truth = np.zeros((probe.N_STATES, 4, frozen.Z))
        self.observed = np.zeros((probe.N_STATES, 4, parent.FEATURES))
        for i in range(4):
            self.truth[:, i, i] = i+1.
            self.observed[:, i, i] = i+1.
        self.std = np.ones(frozen.Z)

    def test_oracle_correct_and_blind_tied(self):
        oracle = probe._score(self.truth, self.truth, self.observed, self.std)
        blind = probe._score(np.zeros_like(self.truth), self.truth,
                             self.observed, self.std)
        self.assertEqual(oracle['informative_pairs'], probe.N_STATES*6)
        self.assertEqual(oracle['correct'], oracle['informative_pairs'])
        self.assertEqual(oracle['wrong']+oracle['tied'], 0)
        self.assertEqual(blind['correct']+blind['wrong'], 0)
        self.assertEqual(blind['tied'], blind['informative_pairs'])

    def test_latent_collapse_excluded_but_reported(self):
        collapsed = self.truth.copy()
        collapsed[:, 1] = collapsed[:, 0]
        r = probe._score(collapsed, collapsed, self.observed, self.std)
        self.assertEqual(r['target_collapsed_pairs'], probe.N_STATES)
        self.assertEqual(r['informative_pairs'], probe.N_STATES*5)
        self.assertEqual(r['correct'], r['informative_pairs'])

    def test_observed_equal_excluded(self):
        obs = self.observed.copy()
        obs[:, 2] = obs[:, 0]
        r = probe._score(self.truth, self.truth, obs, self.std)
        self.assertEqual(r['observed_identical_pairs'], probe.N_STATES)
        self.assertEqual(r['informative_pairs'], probe.N_STATES*5)

    def test_swapped_predictions_cannot_pass_oracle(self):
        pred = self.truth.copy()
        pred[:, [0, 1]] = pred[:, [1, 0]]
        r = probe._score(pred, self.truth, self.observed, self.std)
        self.assertGreater(r['wrong'], 0)

    def test_nonfinite_or_invalid_inputs_fail_closed(self):
        for bad in (self.truth[:1], np.full_like(self.truth, np.nan)):
            with self.assertRaises(ValueError):
                probe._score(bad, bad, self.observed, self.std)
        with self.assertRaises(ValueError):
            probe._score(self.truth, self.truth, self.observed,
                         np.zeros(frozen.Z))


class Run71SourceTests(unittest.TestCase):
    def test_fresh_real_file_cohort_deterministic(self):
        seed = probe.SEEDS[0]
        held = tuple(sorted(random.Random(seed).sample(parent.NON_NOOP, 4)))
        a = probe._paired_states(seed, held)
        b = probe._paired_states(seed, held)
        self.assertEqual(probe._digest(a), probe._digest(b))
        self.assertEqual(len(a), 24)
        self.assertEqual(sum(len(r['candidates']) for r in a), 96)
        self.assertTrue(all(tuple(c[0] for c in r['candidates']) == held
                            for r in a))
        self.assertTrue(any(c[3] for r in a for c in r['candidates']))
        for row in a:
            for action, x2, ok, changed in row['candidates']:
                self.assertEqual(changed, not np.array_equal(row['x'], x2))
                self.assertIs(type(ok), bool)

    def test_invalid_cohort_refused_before_file_actions(self):
        with mock.patch.object(parent, '_rows',
                               side_effect=AssertionError('unexpected file')):
            for kwargs in ({'seeds': (311,)}, {'seeds': [311, 313, 317]},
                           {'n_train': 12}, {'n_states': 12},
                           {'steps': 201}):
                with self.assertRaises(PermissionError):
                    probe.run(**kwargs)

    def test_generator_refuses_unregistered_source(self):
        held = tuple(sorted(random.Random(311).sample(parent.NON_NOOP, 4)))
        for seed, subset in ((999, held), (311, held[:3]),
                             (311, (held[0],)*4)):
            with self.assertRaises(PermissionError):
                probe._paired_states(seed, subset)


class Run71RegisteredResult(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = probe.run()

    def test_fixed_protocol_and_all_negative_gates(self):
        r = self.report
        self.assertEqual(r['schema'], probe.SCHEMA)
        self.assertEqual(r['seeds'], [311, 313, 317])
        self.assertEqual(r['train_rows_per_seed'], 240)
        self.assertEqual(r['paired_source_states_per_seed'], 24)
        self.assertEqual(r['steps'], 200)
        self.assertTrue(r['file_actions_executed'])
        self.assertTrue(r['jepa_training_executed'])
        self.assertFalse(r['supervised_observation_readout_used'])
        for key in ('jepa_only_grounded_utility_proven',
                    'counterfactual_causality_proven',
                    'source_disjointness_verified', 'confidence_measured',
                    'native_model_executed', 'phone_measured',
                    'model_weights_published', 'learning_gate_pass',
                    'whole_system_complete'):
            self.assertFalse(r[key], key)
        self.assertEqual(r['age_authority'], 0)
        self.assertEqual(r['jepa_weight'], 0)

    def test_real_file_models_controls_and_metrics(self):
        for row in self.report['reports']:
            self.assertEqual(row['n_train'], 240)
            self.assertEqual(row['paired_source_states'], 24)
            self.assertEqual(row['candidate_file_actions'], 96)
            self.assertRegex(row['train_rows_sha256'], r'^[a-f0-9]{64}$')
            self.assertRegex(row['paired_rows_sha256'], r'^[a-f0-9]{64}$')
            self.assertEqual(set(row['models']),
                             {'original', 'delta', 'delta_zero_train'})
            for name, model in row['models'].items():
                self.assertTrue(np.isfinite(
                    model['train_target_collapse']['effective_rank']))
                self.assertTrue(np.isfinite(
                    model['train_target_collapse']['min_std']))
                scores = model['scores']
                oracle = scores['oracle_diagnostic']
                blind = scores['blind_diagnostic']
                self.assertEqual(oracle['wrong']+oracle['tied'], 0)
                self.assertEqual(oracle['correct'],
                                 oracle['informative_pairs'])
                self.assertEqual(blind['correct']+blind['wrong'], 0)
                self.assertEqual(blind['tied'], blind['informative_pairs'])
                for s in scores.values():
                    self.assertTrue(np.isfinite(s['normalized_latent_mse']))
                    self.assertGreaterEqual(s['normalized_latent_mse'], 0.)
                    self.assertEqual(s['correct']+s['wrong']+s['tied'],
                                     s['informative_pairs'])
                    self.assertEqual(
                        s['informative_pairs']+s['target_collapsed_pairs']
                        +s['observed_identical_pairs'], 144)
        for model, scores in self.report['aggregate'].items():
            for name, score in scores.items():
                self.assertEqual(score['informative_pairs'],
                                 sum(r['models'][model]['scores'][name]
                                     ['informative_pairs']
                                     for r in self.report['reports']))

    def test_source_digest_replay_without_retraining(self):
        for row in self.report['reports']:
            self.assertEqual(row['paired_rows_sha256'],
                             probe._digest(probe._paired_states(
                                 row['seed'],
                                 tuple(row['heldout_action_indices']))))


if __name__ == '__main__':
    unittest.main()
