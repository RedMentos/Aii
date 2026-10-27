"""Regression: uncalibrated Z12c ablation controls must not invent confidence."""
import ast
import inspect
import unittest

import numpy as np
from scripts import z12c_slot_world_jepa as z12c


class Dummy:
    def __init__(self, calibrated=False):
        self.calls = 0
        self.calibrated = calibrated

    def predict(self, X, A):
        return np.zeros((len(X), z12c.SLOTS, 3)), np.zeros((len(X), z12c.SLOTS))

    def latent(self, X):
        return np.zeros((len(X), z12c.SLOTS, 3))

    def slot_errors(self, X, A, X2):
        return np.zeros((len(X), z12c.SLOTS))

    def confidence(self, X, A):
        self.calls += 1
        if not self.calibrated:
            raise ValueError("No operation calibration: authority forbidden")
        return np.full(len(X), .6), ['MODEL_SIMULATION'] * len(X)


def fixture():
    return [{'x': np.zeros(z12c.SLOTS * 10),
             'cands': [{'a': 0, 'x2': np.zeros(z12c.SLOTS * 10),
                        'snap': ('a',), 'held': False},
                       {'a': 1, 'x2': np.ones(z12c.SLOTS * 10),
                        'snap': ('b',), 'held': True}]}]


class ControlCalibrationRegression(unittest.TestCase):
    def test_untrained_no_action_control_has_no_fabricated_confidence(self):
        m = Dummy()
        out = z12c.cf_eval(m, fixture(), 'zero', calibrated=False)
        self.assertEqual(m.calls, 0)
        self.assertEqual(len(out), 2)
        self.assertEqual([r['conf'] for r in out], [0., 0.])
        self.assertEqual([r['label'] for r in out], ['SIMULATION_UNCERTAIN'] * 2)

    def test_untrained_shuffled_control_has_no_fabricated_confidence(self):
        m = Dummy()
        out = z12c.cf_eval(m, fixture(), 'own', calibrated=False)
        self.assertEqual(m.calls, 0)
        self.assertEqual(len(out), 2)
        self.assertTrue(all(r['label'] == 'SIMULATION_UNCERTAIN' for r in out))

    def test_primary_still_demands_real_calibration(self):
        m = Dummy()
        with self.assertRaisesRegex(ValueError, 'calibration'):
            z12c.cf_eval(m, fixture(), 'own')
        self.assertEqual(m.calls, 1)

    def test_primary_reports_real_calibrated_confidence(self):
        m = Dummy(calibrated=True)
        out = z12c.cf_eval(m, fixture(), 'own')
        self.assertEqual(m.calls, 1)
        self.assertEqual([r['conf'] for r in out], [.6, .6])
        self.assertTrue(all(r['label'] == 'MODEL_SIMULATION' for r in out))

    def test_registered_run_seed_explicitly_marks_both_controls(self):
        tree = ast.parse(inspect.getsource(z12c.run_seed))
        calls = {}
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == 'cf_eval'):
                calls[node.targets[0].id] = node.value
        self.assertEqual(set(calls), {'rec', 'rec0', 'recs'})
        self.assertFalse(any(k.arg == 'calibrated' for k in calls['rec'].keywords))
        for name in ('rec0', 'recs'):
            self.assertTrue(any(k.arg == 'calibrated'
                                and isinstance(k.value, ast.Constant)
                                and k.value.value is False
                                for k in calls[name].keywords))


if __name__ == '__main__':
    unittest.main()
