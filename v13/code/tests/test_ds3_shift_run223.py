"""Run223 preregistered distribution-shift reporting (lab-only, no retuning)."""
import unittest
from v13.agi import ds3_selective as S


def rows(split, high_wrong, low_wrong):
    return ([{'id':f'{split}-hi-{i}', 'split':split,
              'confidence':.95, 'correct':i>=high_wrong} for i in range(300)]
            + [{'id':f'{split}-lo-{i}', 'split':split,
                'confidence':.55, 'correct':i>=low_wrong} for i in range(200)])


def calibration():
    return ([{'id':f'calibration-hi-{i}', 'split':'calibration',
              'confidence':.95, 'correct':i>=10} for i in range(600)]
            + [{'id':f'calibration-lo-{i}', 'split':'calibration',
                'confidence':.55, 'correct':i>=320} for i in range(400)])


class ShiftedSelectiveRiskRun223(unittest.TestCase):
    def test_shifted_high_confidence_errors_must_trigger_explicit_warning(self):
        policy = S.calibrate(calibration())
        self.assertEqual(policy['threshold'], .6)
        report = S.evaluate(rows('shifted-test',270,20), policy)
        self.assertEqual(report['answered'],300)
        self.assertEqual(report['wrong'],270)
        self.assertAlmostEqual(report['selective_risk'],.9)
        self.assertAlmostEqual(report['coverage'],.6)
        self.assertFalse(report['holdout_target_pass'])
        self.assertTrue(report['distribution_shift_warning'])
        self.assertFalse(report['deployment_allowed'])

    def test_original_holdout_pass_is_still_lab_only_not_live_authority(self):
        policy = S.calibrate(calibration())
        report = S.evaluate(rows('original-test',5,150),policy)
        self.assertTrue(report['holdout_target_pass'])
        self.assertFalse(report['distribution_shift_warning'])
        self.assertFalse(report['deployment_allowed'])
        self.assertFalse(report['age_promotion'])
        self.assertFalse(report['external_action_executed'])

    def test_uninformative_calibration_never_deploys_even_if_test_easy(self):
        noise = [{'id':f'noise-{i}', 'split':'calibration',
                  'confidence':.9, 'correct':i>=500} for i in range(1000)]
        policy = S.calibrate(noise)
        report = S.evaluate(rows('easy-test',0,0),policy)
        self.assertEqual(report['answered'],0)
        self.assertFalse(report['holdout_target_pass'])
        self.assertFalse(report['deployment_allowed'])


if __name__=='__main__':
    unittest.main()
