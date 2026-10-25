"""Run196 stratified deployment-veto synthetic software regressions."""
import unittest
from scripts import run196_r4_stratified_abstention as S


def rows(error_compare=0):
    out=[]
    for kind in S.KINDS:
        for i in range(15):
            wrong=kind=='compare' and i<error_compare
            out.append({'fixture':kind+str(i).zfill(2),'pass':not wrong,
                        'tokens':[{'token':'42','logprob':-.2}],
                        'features':{'digit_min_logprob':-.2}})
    return out


class Strata(unittest.TestCase):
    def test_all_four_safe_strata_can_pass_diagnostic_but_no_authority(self):
        result=S.evaluate_strata(rows(),.3)
        self.assertTrue(result['deployment_supported'])
        self.assertEqual(result['production_authority'],0)
        self.assertFalse(result['canonical_gate_pass'])

    def test_compare_unsafe_fails_even_if_global_risk_low(self):
        result=S.evaluate_strata(rows(error_compare=10),.3)
        self.assertFalse(result['deployment_supported'])
        self.assertEqual([x['kind'] for x in result['failures']],['compare'])
        self.assertLess(result['total']['selective_error_rate'],.20)
        self.assertGreater(result['per_kind']['compare']['selective_error_rate'],.30)

    def test_missing_kind_duplicate_and_invalid_threshold_refused(self):
        bad=rows();bad[0]['fixture']='unregistered00'
        with self.assertRaisesRegex(ValueError,'UNREGISTERED_FIXTURE_KIND'):
            S.evaluate_strata(bad,.3)
        bad=rows();bad[1]['fixture']=bad[0]['fixture']
        with self.assertRaisesRegex(ValueError,'FIXTURE_COHORT_INVALID'):
            S.evaluate_strata(bad,.3)
        with self.assertRaisesRegex(ValueError,'THRESHOLD_INVALID'):
            S.evaluate_strata(rows(),float('nan'))

    def test_low_coverage_fails_closed(self):
        x=rows()
        for row in x:
            if row['fixture'].startswith('summary') and int(row['fixture'][7:])<12:
                row['features']['digit_min_logprob']=-2.0
        result=S.evaluate_strata(x,.3)
        self.assertFalse(result['deployment_supported'])
        self.assertIn('TOO_FEW_ANSWERS',result['per_kind']['summary']['reasons'])


if __name__=='__main__':unittest.main()
