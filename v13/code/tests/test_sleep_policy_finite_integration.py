"""Actual Sleep policy/ReplayQueue import checks; full V13 checkout required."""
import unittest
from v13.sleep import default_policy, validate_policy, ReplayQueue


class SleepPolicyIntegration(unittest.TestCase):
    def test_nan_from_operator_parser_fails_before_sample(self):
        p = default_policy()
        p['mix']['recent'] = float('nan')
        with self.assertRaises(ValueError):
            validate_policy(p)

    def test_finite_policy_preserves_replay_selection(self):
        p = validate_policy(default_policy())
        q = ReplayQueue(None)
        st = {'gains': {'EPISODIC': 1.0}, 'items': {
            'new': {'type':'EPISODIC','priority':.9,'retired':None,'next_due':0,
                    'last_outcome':None,'failures':0,'reps':0},
            'old': {'type':'EPISODIC','priority':.8,'retired':None,'next_due':0,
                    'last_outcome':'PASS','failures':0,'reps':1},
        }}
        result = q.sample(st, 2, p['mix'], 1)
        self.assertEqual({k for k,_ in result}, {'new','old'})


if __name__ == '__main__': unittest.main()
