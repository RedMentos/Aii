"""Run222 preregistered DS3 synthetic selective risk/coverage tests.

No native C3 confidence or live authority; see PREREG.md before interpreting.
"""
import math
import unittest

from v13.agi import ds3_selective as S


def cohort(split, high, high_wrong, low, low_wrong):
    out = []
    for i in range(high):
        out.append({'id': f'{split}-hi-{i}', 'split': split,
                    'confidence': .95, 'correct': i >= high_wrong})
    for i in range(low):
        out.append({'id': f'{split}-lo-{i}', 'split': split,
                    'confidence': .55, 'correct': i >= low_wrong})
    return out


class SelectiveRiskLabRun222(unittest.TestCase):
    def setUp(self):
        self.cal = cohort('calibration', 600, 10, 400, 320)
        self.test = cohort('test', 300, 5, 200, 150)

    def test_locked_synthetic_risk_and_coverage_on_disjoint_holdout(self):
        policy = S.calibrate(self.cal)
        self.assertEqual(policy['status'], 'CALIBRATED')
        self.assertEqual(policy['threshold'], .6)
        self.assertLessEqual(policy['risk_upper_bound'], .10)
        report = S.evaluate(self.test, policy)
        self.assertEqual(report['answered'], 300)
        self.assertEqual(report['wrong'], 5)
        self.assertGreaterEqual(report['coverage'], .50)
        self.assertLessEqual(report['selective_risk'], .10)
        self.assertFalse(report['external_action_executed'])
        self.assertFalse(report['age_promotion'])

    def test_uninformative_scores_cannot_claim_confident_answers(self):
        data = [{'id': f'noise-{i}', 'split': 'calibration',
                 'confidence': .9, 'correct': i >= 500}
                for i in range(1000)]
        policy = S.calibrate(data)
        self.assertEqual(policy['status'], 'ABSTAIN_ALL')
        self.assertIsNone(policy['threshold'])
        self.assertEqual(S.decide(.99, policy)['action'], 'ABSTAIN')

    def test_bad_scores_duplicate_ids_and_overlap_fail_closed(self):
        policy = S.calibrate(self.cal)
        for value in (None, True, -1., 1.1, float('nan'), float('inf'), '0.99'):
            with self.subTest(value=str(value)):
                self.assertEqual(S.decide(value, policy)['action'], 'ABSTAIN')
        with self.assertRaises(ValueError):
            S.calibrate(self.cal + [dict(self.cal[0])])
        with self.assertRaises(ValueError):
            S.calibrate([dict(self.cal[0], confidence=float('nan'))])
        with self.assertRaises(ValueError):
            S.calibrate([dict(self.cal[0], split='test')])
        with self.assertRaisesRegex(ValueError, 'OVERLAP'):
            S.evaluate([dict(self.cal[0], split='test')], policy)
        self.assertEqual(S.calibrate(self.cal[:100])['status'], 'ABSTAIN_ALL')

    def test_low_confidence_routes_are_proposals_never_tool_effects(self):
        policy = S.calibrate(self.cal)
        for kwargs, expected in (
            ({}, 'ABSTAIN'),
            ({'ask_user': True}, 'ASK_USER'),
            ({'tool_permitted': True}, 'VERIFY_TOOL_PROPOSAL'),
            ({'tool_permitted': False, 'ask_user': True}, 'ASK_USER'),
        ):
            with self.subTest(kwargs=kwargs):
                decision = S.decide(.55, policy, **kwargs)
                self.assertEqual(decision['action'], expected)
                self.assertFalse(decision['external_action_executed'])
                self.assertEqual(decision['learning_permission'], 'NONE')
        self.assertEqual(S.decide(.95, policy)['action'], 'ANSWER')

    def test_modified_calibration_threshold_must_not_create_answer_authority(self):
        policy = S.calibrate(self.cal)
        forged = dict(policy, threshold=.5)
        self.assertEqual(S.decide(.55, forged)['action'], 'ABSTAIN')
        self.assertEqual(S.decide(.55, policy)['action'], 'ABSTAIN')


if __name__ == '__main__':
    unittest.main()
