"""AG8 finite-score shield must preserve Sleep policy and human approval boundary.

Actual Runtime/SQLite, deterministic synthetic evaluator. No native/Redmi learning.
"""
import math
import tempfile
import unittest
from pathlib import Path

from v13.age import AgeControl
from v13.agi.self_improve import SelfImprovement
from v13.runtime import Runtime
from v13.sleep import LOCKED


class AG8SleepPolicyShieldCrossOrgan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.si = SelfImprovement(
            self.r.store, self.r.cfg, AgeControl(self.r.store, self.r.cfg))
        self.initial = self.r.sleep.cycle.policy()

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def count_requests(self):
        return self.r.store.one(
            "SELECT COUNT(*) AS n FROM requests WHERE kind='SELF_IMPROVEMENT'")['n']

    def propose(self):
        return self.si.propose(
            'learning_rule', {'dream_gain': 0.08}, origin='USER')

    def test_nan_unseen_cannot_schedule_sleep_rule_or_approval(self):
        pid = self.propose()
        baseline = {'overall': .5, 'seen': .5, 'unseen': .5,
                    'forgetting': {'rate': .1}}
        candidate = {'overall': .55, 'seen': .5, 'unseen': math.nan,
                     'forgetting': {'rate': .1}}
        with self.assertRaises(ValueError):
            self.si.evaluate(
                pid, lambda settings: baseline if settings is None else candidate)
        self.assertEqual(self.si.get(pid)['status'], 'PROPOSED')
        self.assertEqual(self.count_requests(), 0)
        self.assertEqual(self.r.sleep.cycle.policy(), self.initial)
        for key, value in LOCKED.items():
            self.assertEqual(self.r.sleep.cycle.policy()[key], value)
        self.assertEqual(self.r.store.rows('SELECT * FROM updates'), [])

    def test_finite_improvement_still_requires_human_and_does_not_auto_apply(self):
        pid = self.propose()
        baseline = {'overall': .5, 'seen': .5, 'unseen': .5,
                    'forgetting': {'rate': .1}}
        candidate = {'overall': .55, 'seen': .5, 'unseen': .5,
                     'forgetting': {'rate': .1}}
        result = self.si.evaluate(
            pid, lambda settings: baseline if settings is None else candidate)
        self.assertEqual(result['status'], 'PENDING_USER')
        self.assertEqual(self.count_requests(), 1)
        self.assertEqual(self.r.sleep.cycle.policy(), self.initial)
        self.assertEqual(self.r.store.rows('SELECT * FROM updates'), [])


if __name__ == '__main__':
    unittest.main()
