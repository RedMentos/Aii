"""Run484 independent cross-review: fail-closed HX5 retention and acceptance."""
import math
import unittest
from v13.agi.harness_data import item, retention_gate


def good():
    return {'base_eval': {'overall': .8, 'unseen': .7},
            'candidate_eval': {'overall': .79, 'unseen': .70,
                               'forgetting': {'rate': .0}},
            'learned_recall': .9, 'base_recall': .2,
            'near_miss_leak': .0, 'kl_to_base': .05}


class RetentionFailClosed(unittest.TestCase):
    def test_valid_evidence_still_passes_with_explicit_kl(self):
        r=retention_gate(good(),max_kl=.1)
        self.assertEqual(r['status'],'RETENTION_PASS')
        self.assertTrue(r['kl_checked'])

    def test_missing_every_metric_cannot_pass(self):
        r=retention_gate({'learned_recall':.9,'base_recall':.2})
        self.assertEqual(r['status'],'RETENTION_FAIL')
        self.assertTrue({'retention_overall','retention_unseen',
                         'forgetting','near_miss_leak'}.issubset(r['fails']))
        self.assertFalse(r['kl_checked'])

    def test_nan_metrics_never_pass(self):
        for place in ('overall','unseen','forgetting','near_miss_leak','kl'):
            ev=good()
            if place in ('overall','unseen'):
                ev['candidate_eval'][place]=float('nan')
            elif place=='forgetting':
                ev['candidate_eval']['forgetting']['rate']=float('nan')
            elif place=='near_miss_leak':
                ev['near_miss_leak']=float('nan')
            else:
                ev['kl_to_base']=float('nan')
            with self.subTest(place=place):
                self.assertEqual(retention_gate(ev,max_kl=.1)['status'],'RETENTION_FAIL')

    def test_bool_and_negative_metrics_never_pass(self):
        for value in (True,False,-.01,float('inf')):
            ev=good();ev['candidate_eval']['overall']=value
            with self.subTest(value=value):
                self.assertIn('retention_overall',retention_gate(ev)['fails'])

    def test_missing_base_cannot_claim_retention(self):
        ev=good();del ev['base_eval']
        r=retention_gate(ev)
        self.assertIn('retention_overall',r['fails'])
        self.assertIn('retention_unseen',r['fails'])

    def test_bad_thresholds_fail_closed(self):
        for tol in (float('nan'),True,-.01,1.1):
            with self.subTest(tol=tol):
                self.assertIn('invalid_tolerance',retention_gate(good(),tol=tol)['fails'])
        for bound in (float('nan'),True,-.01):
            with self.subTest(bound=bound):
                self.assertIn('invalid_kl_threshold',retention_gate(good(),max_kl=bound)['fails'])

    def test_missing_kl_fails_when_explicit_bound_requested(self):
        ev=good();del ev['kl_to_base']
        self.assertIn('kl_to_base',retention_gate(ev,max_kl=.1)['fails'])

    def test_acceptance_must_be_actual_boolean(self):
        rec={'messages':[{'role':'system','content':'Context.'},
                         {'role':'user','content':'Question.'}],
             'output':'Answer.','accepted':True}
        self.assertEqual(item(rec)['target'],'Answer.')
        self.assertIsNone(item(dict(rec,accepted=False)))
        for invalid in ('true','false',1,0,None,[],{}):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                item(dict(rec,accepted=invalid))

    def test_malformed_message_row_rejected(self):
        rec={'messages':['not a mapping'],'output':'Answer.','accepted':True}
        with self.assertRaises(ValueError):item(rec)


if __name__=='__main__':
    unittest.main()
