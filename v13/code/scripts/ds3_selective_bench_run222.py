#!/usr/bin/env python3
"""Run222 locked synthetic DS3 cohort; no native C3 or live decision authority."""
import json
from v13.agi.ds3_selective import calibrate, evaluate, decide, REVISION


def cohort(split, high, high_wrong, low, low_wrong):
    return ([{'id':f'{split}-hi-{i}', 'split':split,
              'confidence':.95, 'correct':i>=high_wrong} for i in range(high)]
            + [{'id':f'{split}-lo-{i}', 'split':split,
                'confidence':.55, 'correct':i>=low_wrong} for i in range(low)])


def main():
    calibration = cohort('calibration',600,10,400,320)
    holdout = cohort('test',300,5,200,150)
    policy = calibrate(calibration)
    report = evaluate(holdout,policy)
    noise = calibrate([{'id':f'noise-{i}', 'split':'calibration',
                        'confidence':.9, 'correct':i>=500} for i in range(1000)])
    verdict = {
        'revision': REVISION, 'evidence': 'SYNTHETIC_LINUX_LAB_ONLY',
        'calibration': policy, 'heldout': report,
        'uninformative': {'status':noise['status'], 'threshold':noise['threshold']},
        'hypotheses': {
            'H1_risk_coverage': policy['status']=='CALIBRATED'
                 and report['selective_risk'] is not None
                 and report['selective_risk']<=.10 and report['coverage']>=.50,
            'H2_noise_abstains': noise['status']=='ABSTAIN_ALL',
            'H3_no_tool_effects': not decide(.55,policy,tool_permitted=True)['external_action_executed'],
            'H4_no_authority_promotion': not report['age_promotion']
        },
        'gates': {'STEP2':'UTILITY_FAIL','B3_L1':'FAIL',
                  'Body_JEPA':'UNAVAILABLE','jepa_weight':0,
                  'V13':'INCOMPLETE'},
        'native_c3_confidence': 'NOT_MEASURED',
        'redmi': 'NOT_RUN',
    }
    verdict['all_lab_hypotheses_pass'] = all(verdict['hypotheses'].values())
    print(json.dumps(verdict,sort_keys=True))
    return 0 if verdict['all_lab_hypotheses_pass'] else 2


if __name__=='__main__':
    raise SystemExit(main())
