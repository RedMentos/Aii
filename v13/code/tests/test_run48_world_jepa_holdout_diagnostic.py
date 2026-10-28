"""Run48 synthetic World-JEPA holdout diagnostic; no native or utility promotion."""
import hashlib
import math
import unittest

import numpy as np

from v13 import world_jepa as wj
from v13 import world_jepa_holdout_diagnostic as audit

TRAIN = hashlib.sha256(b'run48 synthetic training source').hexdigest()
HOLDOUT = hashlib.sha256(b'run48 synthetic holdout source').hexdigest()


class Run48HoldoutDiagnostic(unittest.TestCase):
    def setUp(self):
        self.x = np.zeros((16, 2), dtype=float)
        self.a = np.eye(2)[np.arange(16) % 2]
        self.x2 = self.x + self.a
        self.model = wj.WorldJEPA(seed=2, ensemble=1).fit(
            self.x, self.a, self.x2, steps=1, log_every=1)

    def evaluate(self, model=None, x=None, a=None, x2=None, **pins):
        return audit.evaluate(self.model if model is None else model,
                              self.x if x is None else x,
                              self.a if a is None else a,
                              self.x2 if x2 is None else x2,
                              train_source_sha256=pins.get('train', TRAIN),
                              holdout_source_sha256=pins.get('holdout', HOLDOUT))

    def test_real_one_step_is_only_diagnostic_not_learning_proof(self):
        report = self.evaluate()
        self.assertEqual(report['status'], 'SHADOW_OBSERVATION_ONLY')
        self.assertEqual(report['fit_steps'], 1)
        self.assertFalse(report['utility_proven'])
        self.assertFalse(report['source_disjointness_verified'])
        self.assertFalse(report['learning_gate_pass'])
        self.assertEqual(report['age_authority'], 0)
        self.assertEqual(report['n_rows'], 16)
        self.assertEqual(len(report['model_state_sha256']), 64)
        self.assertTrue(all(math.isfinite(v) for v in report['metrics'].values()))

    def test_exact_action_toy_separates_wrong_action_and_persistence(self):
        # The fitted model supplies a complete source-bound state, but its
        # read-only inference methods are replaced with a perfect synthetic
        # oracle. This tests the *diagnostic arithmetic*, not model learning.
        def pad(v):
            return np.pad(v, ((0, 0), (0, wj.Z - 2)))

        self.model.latent = lambda x, target=True: pad(x)
        self.model.predict = lambda x, a: (pad(x + a), np.zeros(len(x)))
        report = self.evaluate()
        self.assertEqual(report['metrics']['correct_action_mse'], 0.)
        self.assertGreater(report['metrics']['different_supported_action_mse'], 0.)
        self.assertGreater(report['metrics']['persistence_mse'], 0.)
        self.assertGreater(report['metrics']['action_sensitivity_delta'], 0.)
        self.assertGreater(report['metrics']['persistence_gain_delta'], 0.)
        self.assertFalse(report['utility_proven'])

    def test_repeated_reads_are_deterministic_and_do_not_mutate_weights(self):
        before = self.model.enc['W1'].copy()
        first = self.evaluate()
        second = self.evaluate()
        self.assertEqual(first, second)
        np.testing.assert_array_equal(self.model.enc['W1'], before)

    def test_zero_step_and_legacy_unknown_steps_have_no_metrics(self):
        self.model._fit_steps = 0
        report = self.evaluate()
        self.assertEqual(report['status'], 'NO_TRAINING_EVIDENCE')
        self.assertIsNone(report['metrics'])
        self.model.__dict__.pop('_fit_steps')
        self.assertEqual(self.evaluate()['status'], 'NO_TRAINING_EVIDENCE')

    def test_invalid_pins_and_holdout_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'SOURCE_SHA256'):
            self.evaluate(train='not-a-digest')
        for wrong in (self.a.copy(),):
            wrong[0] = [1, 1]
            with self.assertRaisesRegex(ValueError, 'INVALID_HOLDOUT'):
                self.evaluate(a=wrong)
        nan = self.x.copy()
        nan[0, 0] = float('nan')
        with self.assertRaisesRegex(ValueError, 'INVALID_HOLDOUT'):
            self.evaluate(x=nan)
        with self.assertRaisesRegex(ValueError, 'TWO_ACTION'):
            self.evaluate(a=np.tile([[1., 0.]], (16, 1)))
        with self.assertRaisesRegex(ValueError, 'INVALID_HOLDOUT'):
            self.evaluate(x=self.x[:7], a=self.a[:7], x2=self.x2[:7])

    def test_unseen_training_action_does_not_claim_quality(self):
        self.model._action_counts[1] = 0
        report = self.evaluate()
        self.assertEqual(report['status'], 'INSUFFICIENT_TRAIN_ACTION_SUPPORT')
        self.assertIsNone(report['metrics'])
        self.assertFalse(report['utility_proven'])


if __name__ == '__main__':
    unittest.main()
